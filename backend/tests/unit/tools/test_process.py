import multiprocessing
import os
import time
from pathlib import Path

import pytest

from backend.app.contracts.models import DatasetReference, PlanStep
from backend.app.tools.analysis.descriptive import default_registry
from backend.app.tools.process import run_isolated
from backend.app.tools.registry import execute_step


def reference() -> DatasetReference:
    return DatasetReference(
        dataset_id="test", version="raw", storage_ref="unused.csv", schema={}
    )


def echo(dataset: DatasetReference, **arguments: object) -> dict:
    return {"sample_size": 1, **arguments}


def slow(dataset: DatasetReference, **arguments: object) -> dict:
    time.sleep(10)
    Path(arguments["completion_path"]).write_text("completed")
    return {}


def disconnected(dataset: DatasetReference, **arguments: object) -> dict:
    raise ConnectionError("private connection details")


def crash(dataset: DatasetReference, **arguments: object) -> dict:
    os._exit(1)


def test_isolated_tool_returns_large_payload_without_pipe_deadlock() -> None:
    value = "x" * 2_000_000

    result = run_isolated(echo, reference(), {"value": value}, 10)

    assert result == {"sample_size": 1, "value": value}


def test_deadline_stops_worker_before_returning(tmp_path: Path) -> None:
    completed = tmp_path / "completed"
    before = {child.pid for child in multiprocessing.active_children()}
    start = time.monotonic()

    with pytest.raises(TimeoutError):
        run_isolated(slow, reference(), {"completion_path": str(completed)}, 0.2)

    assert time.monotonic() - start < 3
    assert not completed.exists()
    assert {child.pid for child in multiprocessing.active_children()} == before


@pytest.mark.parametrize(
    "run,error", [(disconnected, ConnectionError), (crash, ValueError)]
)
def test_worker_failures_return_safe_errors(run, error) -> None:
    with pytest.raises(error) as captured:
        run_isolated(run, reference(), {}, 10)

    assert "private" not in str(captured.value)


def test_production_registry_executes_real_tool_in_a_process() -> None:
    path = Path(__file__).resolve().parents[2] / "fixtures" / "clean.csv"
    dataset = DatasetReference(
        dataset_id="ages",
        version="raw",
        storage_ref=str(path),
        schema={"age": {"datatype": "integer"}},
    )

    result = execute_step(
        PlanStep(
            step_id="stats",
            tool_name="descriptive_statistics",
            arguments={"columns": ["age"]},
        ),
        dataset,
        default_registry(isolate_execution=True),
    )

    assert result.values["columns"]["age"]["mean"] == 20
    assert result.sample_size == 3
