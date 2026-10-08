from pathlib import Path

from backend.app.agents.analysis import execute_step
from backend.app.contracts.models import DatasetReference, PlanStep
from backend.app.tools.analysis.descriptive import default_registry
from backend.app.tools.analysis.top_n import run

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


def test_top_n_returns_largest_values_by_default():
    payload = run(
        _dataset(),
        column="units",
        n=2,
    )

    assert [row["units"] for row in payload["rows"]] == [4, 3]
    assert payload["row_count"] == 2
    assert payload["sample_size"] == 4


def test_top_n_can_return_smallest_values():
    payload = run(
        _dataset(),
        column="units",
        n=2,
        descending=False,
    )

    assert [row["units"] for row in payload["rows"]] == [1, 2]


def test_top_n_rejects_unknown_column():
    result = execute_step(
        PlanStep(
            step_id="top",
            tool_name="top_n",
            arguments={
                "column": "missing",
                "n": 2,
            },
        ),
        _dataset(),
        default_registry(),
    )

    assert result.values["code"] == "MISSING_COLUMN"
    assert result.values["status"] == "failed"
