from pathlib import Path

from backend.app.agents.analysis import execute_step
from backend.app.contracts.models import DatasetReference, PlanStep
from backend.app.tools.analysis.compare_groups import run
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


def test_compare_groups_returns_summary_statistics():
    payload = run(
        _dataset(),
        group_by="region",
        values="revenue",
    )

    assert payload["groups"] == [
        {
            "region": "North",
            "count": 1,
            "mean": 10.0,
            "median": 10.0,
            "std": None,
            "min": 10.0,
            "max": 10.0,
        },
        {
            "region": "South",
            "count": 1,
            "mean": 30.0,
            "median": 30.0,
            "std": None,
            "min": 30.0,
            "max": 30.0,
        },
        {
            "region": None,
            "count": 1,
            "mean": 40.0,
            "median": 40.0,
            "std": None,
            "min": 40.0,
            "max": 40.0,
        },
    ]
    assert payload["group_count"] == 3
    assert payload["sample_size"] == 4


def test_compare_groups_rejects_unknown_group_column():
    result = execute_step(
        PlanStep(
            step_id="compare",
            tool_name="compare_groups",
            arguments={
                "group_by": "missing",
                "values": "revenue",
            },
        ),
        _dataset(),
        default_registry(),
    )

    assert result.values["code"] == "MISSING_COLUMN"
    assert result.values["status"] == "failed"


def test_compare_groups_rejects_non_numeric_values():
    result = execute_step(
        PlanStep(
            step_id="compare",
            tool_name="compare_groups",
            arguments={
                "group_by": "region",
                "values": "segment",
            },
        ),
        _dataset(),
        default_registry(),
    )

    assert result.values["code"] == "INVALID_DATA"
    assert result.values["status"] == "failed"
