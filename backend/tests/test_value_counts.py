from pathlib import Path

from backend.app.agents.analysis import execute_step
from backend.app.contracts.models import DatasetReference, PlanStep
from backend.app.tools.analysis.descriptive import default_registry
from backend.app.tools.analysis.value_counts import run

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


def test_value_counts_counts_observed_values():
    payload = run(_dataset(), column="region")

    assert payload["values"] == [
        {"value": "North", "count": 2},
        {"value": "South", "count": 1},
    ]
    assert payload["unique_count"] == 2
    assert payload["sample_size"] == 4
    assert payload["warnings"] == []


def test_value_counts_accepts_numeric_columns():
    result = execute_step(
        PlanStep(
            step_id="unit-counts",
            tool_name="value_counts",
            arguments={"column": "units"},
        ),
        _dataset(),
        default_registry(),
    )

    assert result.values["status"] == "ok"
    assert result.method == "value_counts"
    assert result.sample_size == 4


def test_value_counts_rejects_unknown_column_before_execution():
    result = execute_step(
        PlanStep(
            step_id="counts",
            tool_name="value_counts",
            arguments={"column": "missing"},
        ),
        _dataset(),
        default_registry(),
    )

    assert result.values["code"] == "MISSING_COLUMN"
    assert result.values["status"] == "failed"
