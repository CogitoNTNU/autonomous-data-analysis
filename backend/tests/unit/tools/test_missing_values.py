from pathlib import Path

import pytest

from backend.app.agents.analysis.agent import run_analysis
from backend.app.agents.planner.agent import run_planner
from backend.app.agents.planner.schema import PlannerOutput
from backend.app.contracts.models import DatasetReference, Plan, PlanStep
from backend.app.tools.analysis.descriptive import default_registry


def dataset(path: Path) -> DatasetReference:
    return DatasetReference(
        dataset_id="missing-values",
        version="raw",
        storage_ref=str(path),
        schema={
            "name": {"datatype": "string"},
            "amount": {"datatype": "float"},
        },
    )


def step(columns: list[str]) -> PlanStep:
    return PlanStep(
        step_id="missing",
        tool_name="missing_values_summary",
        arguments={"columns": columns},
    )


def test_missing_values_question_produces_traceable_analysis_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "backend.app.tools.analysis.files.ALLOWED_DATA_DIRECTORIES", (tmp_path,)
    )
    path = tmp_path / "mixed.csv"
    contents = "name,amount\nA,1\n,2\nB,\n"
    path.write_text(contents)
    reference = dataset(path)
    plan = Plan(
        plan_id="missing-plan",
        objective="Which columns contain missing values?",
        analysis_steps=[step(["name", "amount"])],
    )
    registry = default_registry()

    planned = run_planner(
        plan.objective,
        reference,
        [],
        None,
        registry,
        lambda prompt, context: PlannerOutput(plan=plan),
    )
    assert planned.status == "success"
    engine = run_analysis(
        reference, planned.updates.plan.analysis_steps, registry=registry
    )

    assert engine.response.status == "success"
    result = engine.response.updates.analysis_results[0]
    assert result.step_id == "missing"
    assert result.dataset_version == "raw"
    assert result.sample_size == 3
    assert result.values["columns"] == {
        "name": {"missing_count": 1, "observed_count": 2, "missing_rate": 1 / 3},
        "amount": {"missing_count": 1, "observed_count": 2, "missing_rate": 1 / 3},
    }
    assert path.read_text() == contents


@pytest.mark.parametrize("columns", [[], ["unknown"]])
def test_missing_values_rejects_invalid_columns(columns: list[str]) -> None:
    engine = run_analysis(
        dataset(Path("unused.csv")), [step(columns)], registry=default_registry()
    )

    assert engine.response.status == "error"
    assert engine.response.updates.analysis_results[0].values["status"] == "failed"


def test_empty_dataset_has_undefined_missing_rate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "backend.app.tools.analysis.files.ALLOWED_DATA_DIRECTORIES", (tmp_path,)
    )
    path = tmp_path / "empty.csv"
    path.write_text("name,amount\n")

    engine = run_analysis(dataset(path), [step(["name"])], registry=default_registry())

    result = engine.response.updates.analysis_results[0]
    assert engine.response.status == "success"
    assert result.sample_size == 0
    assert result.values["columns"]["name"] == {
        "missing_count": 0,
        "observed_count": 0,
        "missing_rate": None,
    }
