from pathlib import Path

from backend.app.agents.analysis import execute_step
from backend.app.contracts.models import DatasetReference, PlanStep
from backend.app.tools.analysis.group_aggregate import run
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


def test_group_aggregate_calculates_named_aggregations():
    payload = run(
        _dataset(),
        group_by=["region"],
        aggregations=[
            {"column": "revenue", "function": "mean", "alias": "mean_revenue"},
            {"column": "units", "function": "sum", "alias": "total_units"},
        ],
    )

    assert payload["sample_size"] == 4
    assert payload["group_count"] == 3
    assert payload["groups"] == [
        {"region": "North", "mean_revenue": 10.0, "total_units": 3},
        {"region": "South", "mean_revenue": 30.0, "total_units": 3},
        {"region": None, "mean_revenue": 40.0, "total_units": 4},
    ]


def test_group_aggregate_preserves_missing_groups_and_reports_missing_data():
    payload = run(
        _dataset(),
        group_by=["region", "segment"],
        aggregations=[{"column": "revenue", "function": "count", "alias": "observed"}],
    )

    codes = {warning.code for warning in payload["warnings"]}
    assert payload["groups"][-1] == {
        "region": None,
        "segment": "A",
        "observed": 1,
    }
    assert {"HIGH_MISSING_RATE", "MISSING_GROUP_VALUES"} <= codes


def test_group_aggregate_rejects_unknown_group_column_before_execution():
    result = execute_step(
        PlanStep(
            step_id="group",
            tool_name="group_aggregate",
            arguments={
                "group_by": ["missing"],
                "aggregations": [
                    {
                        "column": "revenue",
                        "function": "mean",
                        "alias": "mean_revenue",
                    }
                ],
            },
        ),
        _dataset(),
        default_registry(),
    )

    assert result.values["code"] == "MISSING_COLUMN"
    assert result.values["status"] == "failed"


def test_group_aggregate_rejects_non_numeric_aggregation_column():
    result = execute_step(
        PlanStep(
            step_id="group",
            tool_name="group_aggregate",
            arguments={
                "group_by": ["region"],
                "aggregations": [
                    {"column": "segment", "function": "mean", "alias": "invalid"}
                ],
            },
        ),
        _dataset(),
        default_registry(),
    )

    assert result.values["code"] == "INVALID_DATA"
    assert "segment" in result.values["error"]
