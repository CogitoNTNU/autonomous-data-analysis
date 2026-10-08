from pathlib import Path

from backend.app.agents.analysis import execute_step
from backend.app.contracts.models import DatasetReference, PlanStep
from backend.app.tools.analysis.descriptive import default_registry
from backend.app.tools.analysis.pivot_table import run

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


def test_pivot_table_returns_expected_rows():
    payload = run(
        _dataset(),
        index="region",
        columns="segment",
        values="revenue",
        function="mean",
    )

    assert payload["rows"] == [
        {"region": "North", "A": 10.0, "B": None},
        {"region": "South", "A": 30.0, "B": None},
        {"region": None, "A": 40.0, "B": None},
    ]
    assert payload["row_count"] == 3
    assert payload["sample_size"] == 4


def test_pivot_table_rejects_unknown_value_column():
    result = execute_step(
        PlanStep(
            step_id="pivot",
            tool_name="pivot_table",
            arguments={
                "index": "region",
                "columns": "segment",
                "values": "missing",
                "function": "mean",
            },
        ),
        _dataset(),
        default_registry(),
    )

    assert result.values["code"] == "MISSING_COLUMN"
    assert result.values["status"] == "failed"


def test_pivot_table_rejects_non_numeric_values():
    result = execute_step(
        PlanStep(
            step_id="pivot",
            tool_name="pivot_table",
            arguments={
                "index": "region",
                "columns": "segment",
                "values": "segment",
                "function": "mean",
            },
        ),
        _dataset(),
        default_registry(),
    )

    assert result.values["code"] == "INVALID_DATA"
    assert "segment" in result.values["error"]
