from pathlib import Path

import pytest

from backend.app.agents.analysis import execute_step, run_analysis
from backend.app.contracts.models import DatasetReference, PlanStep, PreprocessingReport
from backend.app.tools.analysis.categorical import run
from backend.app.tools.analysis.descriptive import default_registry

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SCHEMA = {
    "region": {"datatype": "string"},
    "segment": {"datatype": "string"},
    "revenue": {"datatype": "float"},
    "units": {"datatype": "integer"},
}


def _dataset() -> DatasetReference:
    return DatasetReference(
        dataset_id="grouped",
        version="v1",
        storage_ref=str(FIXTURES / "grouped.csv"),
        schema=SCHEMA,
    )


def test_categorical_analysis_counts_observed_values():
    payload = run(_dataset(), column="region", normalize=False)

    assert payload["categories"] == [
        {"value": "North", "count": 2},
        {"value": "South", "count": 1},
    ]
    assert payload["category_count"] == 2
    assert payload["observed_count"] == 3
    assert payload["missing_count"] == 1
    assert payload["sample_size"] == 4
    assert {warning.code for warning in payload["warnings"]} >= {
        "HIGH_MISSING_RATE",
        "LOW_SAMPLE_SIZE",
    }


def test_categorical_analysis_normalizes_by_observed_values():
    payload = run(_dataset(), column="segment", normalize=True)

    assert payload["categories"] == [
        {"value": "A", "proportion": pytest.approx(0.75)},
        {"value": "B", "proportion": pytest.approx(0.25)},
    ]
    assert payload["normalized"] is True
    assert payload["missing_count"] == 0


def test_categorical_analysis_rejects_unknown_column_before_execution():
    result = execute_step(
        PlanStep(
            step_id="categories",
            tool_name="categorical_analysis",
            arguments={"column": "missing", "normalize": False},
        ),
        _dataset(),
        default_registry(),
    )

    assert result.values["code"] == "MISSING_COLUMN"
    assert result.values["status"] == "failed"


def test_categorical_analysis_rejects_numeric_column():
    result = execute_step(
        PlanStep(
            step_id="categories",
            tool_name="categorical_analysis",
            arguments={"column": "units", "normalize": False},
        ),
        _dataset(),
        default_registry(),
    )

    assert result.values["code"] == "INVALID_DATA"
    assert "units" in result.values["error"]


def test_analysis_agent_uses_preprocessed_dataset_for_categorical_step():
    preprocessing_report = PreprocessingReport(
        changes=["Removed one incomplete row"],
        affected_columns=["region"],
        rows_before=5,
        rows_after=4,
    )
    step = PlanStep(
        step_id="region-distribution",
        tool_name="categorical_analysis",
        arguments={"column": "region", "normalize": False},
    )

    engine = run_analysis(
        _dataset(),
        [step],
        preprocessing_report,
        registry=default_registry(),
    )

    result = engine.response.updates.analysis_results[0]
    assert result.step_id == "region-distribution"
    assert result.dataset_version == "v1"
    assert result.method == "categorical_analysis"
    assert result.sample_size == 4
    assert result.values["categories"] == [
        {"value": "North", "count": 2},
        {"value": "South", "count": 1},
    ]
    assert engine.missing_steps == []
    assert engine.execution_log == [
        "preprocessing 5->4",
        "running region-distribution",
        "ok region-distribution",
    ]
