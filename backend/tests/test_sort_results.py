from pathlib import Path

from backend.app.agents.analysis import execute_step
from backend.app.contracts.models import DatasetReference, PlanStep
from backend.app.tools.analysis.descriptive import default_registry
from backend.app.tools.analysis.sort_results import run

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


def test_sort_results_sorts_numeric_column_descending():
    payload = run(
        _dataset(),
        column="units",
        descending=True,
    )

    assert [row["units"] for row in payload["rows"]] == [4, 3, 2, 1]
    assert payload["row_count"] == 4
    assert payload["sample_size"] == 4


def test_sort_results_sorts_string_column_ascending():
    payload = run(
        _dataset(),
        column="segment",
    )

    assert [row["segment"] for row in payload["rows"]] == ["A", "A", "A", "B"]


def test_sort_results_rejects_unknown_column():
    result = execute_step(
        PlanStep(
            step_id="sort",
            tool_name="sort_results",
            arguments={
                "column": "missing",
                "descending": True,
            },
        ),
        _dataset(),
        default_registry(),
    )

    assert result.values["code"] == "MISSING_COLUMN"
    assert result.values["status"] == "failed"
