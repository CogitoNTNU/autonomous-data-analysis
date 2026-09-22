from unittest.mock import Mock
import time

from pydantic import BaseModel, Field

from backend.app.agents.analysis import execute_step, run_analysis
from backend.app.contracts.models import DatasetReference, PlanStep, PreprocessingReport
from backend.app.tools.registry import Tool, ToolRegistry

NUMERIC = frozenset({"integer", "float"})


class ColumnsInput(BaseModel):
    columns: list[str] = Field(min_length=1)


def _dataset(**schema: dict) -> DatasetReference:
    return DatasetReference(
        dataset_id="test",
        version="v1",
        storage_ref="unused.csv",
        schema=schema or {"age": {"datatype": "integer"}, "bad": {"datatype": "float"}},
    )


def _registry(run) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        Tool(
            name="descriptive_statistics",
            description="stats",
            input_model=ColumnsInput,
            accepted_dtypes=NUMERIC,
            run=run,
        )
    )
    return registry


def test_unknown_column_is_rejected_before_the_tool_runs():
    tool = Mock(return_value={"columns": {}})
    result = execute_step(
        PlanStep(
            step_id="s1",
            tool_name="descriptive_statistics",
            arguments={"columns": ["missing_col"]},
        ),
        _dataset(age={"datatype": "integer"}),
        _registry(tool),
    )
    tool.assert_not_called()
    assert result.values["code"] == "MISSING_COLUMN"
    assert result.values["status"] == "failed"


def test_wrong_dtype_is_rejected_before_the_tool_runs():
    tool = Mock(return_value={"columns": {}})
    result = execute_step(
        PlanStep(
            step_id="s1",
            tool_name="descriptive_statistics",
            arguments={"columns": ["city"]},
        ),
        _dataset(city={"datatype": "string"}, age={"datatype": "integer"}),
        _registry(tool),
    )
    tool.assert_not_called()
    assert result.values["code"] == "INVALID_DATA"
    assert "city" in result.values["error"]


def test_step_is_skipped_when_dependency_fails():
    def run(dataset_ref, **kwargs):
        if kwargs["columns"] == ["bad"]:
            raise RuntimeError("cannot analyze bad")
        return {"columns": {"age": {"mean": 10.0, "n": 2}}, "sample_size": 2}

    engine = run_analysis(
        _dataset(),
        [
            PlanStep(
                step_id="a",
                tool_name="descriptive_statistics",
                arguments={"columns": ["bad"]},
            ),
            PlanStep(
                step_id="b",
                tool_name="descriptive_statistics",
                arguments={"columns": ["age"]},
                depends_on=["a"],
            ),
            PlanStep(
                step_id="c",
                tool_name="descriptive_statistics",
                arguments={"columns": ["age"]},
            ),
        ],
        PreprocessingReport(rows_before=2, rows_after=2),
        registry=_registry(run),
    )
    ids = [item.step_id for item in engine.response.updates.analysis_results]
    assert engine.missing_steps == ["b"]
    assert ids == ["a", "c"]
    assert engine.response.status == "success"
    assert engine.execution_log
    assert any("skipped b" in line for line in engine.execution_log)
    assert any(
        item.values["status"] == "failed"
        for item in engine.response.updates.analysis_results
        if item.step_id == "a"
    )


def test_unchanged_parameters_are_served_from_cache():
    tool = Mock(return_value={"columns": {"age": {"mean": 1.0}}, "sample_size": 3})
    steps = [
        PlanStep(
            step_id="s1",
            tool_name="descriptive_statistics",
            arguments={"columns": ["age"]},
        ),
        PlanStep(
            step_id="s2",
            tool_name="descriptive_statistics",
            arguments={"columns": ["age"]},
        ),
    ]
    engine = run_analysis(_dataset(), steps, registry=_registry(tool))
    assert tool.call_count == 1
    results = engine.response.updates.analysis_results
    assert [item.step_id for item in results] == ["s1", "s2"]
    assert results[0].values["columns"] == results[1].values["columns"]
    assert any("cache" in line for line in engine.execution_log)


def test_timeout_returns_failed_result_instead_of_raising():
    def slow_tool(dataset_ref, **kwargs):
        time.sleep(1)
        return {"columns": {}}

    result = execute_step(
        PlanStep(
            step_id="slow",
            tool_name="descriptive_statistics",
            arguments={"columns": ["age"]},
        ),
        _dataset(),
        _registry(slow_tool),
        timeout_seconds=0.05,
    )
    assert result.values["code"] == "TIMEOUT"
    assert result.values["status"] == "failed"


def test_tool_receives_stable_random_state():
    tool = Mock(return_value={"columns": {"age": {"mean": 1.0}}, "sample_size": 1})
    execute_step(
        PlanStep(
            step_id="s1",
            tool_name="descriptive_statistics",
            arguments={"columns": ["age"]},
        ),
        _dataset(),
        _registry(tool),
    )
    assert tool.call_args.kwargs["random_state"] == 0


def test_tool_artifacts_are_collected():
    tool = Mock(
        return_value={
            "columns": {"age": {"mean": 1.0}},
            "sample_size": 1,
            "artifacts": [
                {"artifact_id": "t1", "type": "table", "storage_ref": "memory://t1"}
            ],
        }
    )
    engine = run_analysis(
        _dataset(),
        [
            PlanStep(
                step_id="s1",
                tool_name="descriptive_statistics",
                arguments={"columns": ["age"]},
            )
        ],
        registry=_registry(tool),
    )
    assert len(engine.response.updates.artifacts) == 1
    assert engine.response.updates.artifacts[0].artifact_id == "t1"
