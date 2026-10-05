from pathlib import Path

from backend.app.agents.analysis import execute_step
from backend.app.contracts.models import DatasetReference, PlanStep
from backend.app.tools.analysis.descriptive import default_registry
from backend.app.tools.analysis.time_series import run

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _dataset(name: str) -> DatasetReference:
    return DatasetReference(
        dataset_id="time-series-fixture",
        version="v1",
        storage_ref=str(FIXTURES / name),
        schema={
            "date": {"datatype": "date"},
            "revenue": {"datatype": "float"},
        },
    )


def test_time_series_analysis_aggregates_monthly_sum() -> None:
    payload = run(
        _dataset("time_series.csv"),
        date_column="date",
        value_column="revenue",
        frequency="monthly",
        aggregation="sum",
    )

    assert payload["sample_size"] == 4
    assert payload["start_date"] == "2024-01-01"
    assert payload["end_date"] == "2024-02-20"
    assert payload["series"] == [
        {
            "period": "2024-01",
            "period_start": "2024-01-01",
            "period_end": "2024-01-31",
            "value": 30.0,
            "observation_count": 2,
        },
        {
            "period": "2024-02",
            "period_start": "2024-02-01",
            "period_end": "2024-02-29",
            "value": 20.0,
            "observation_count": 2,
        },
    ]


def test_time_series_analysis_rejects_unsupported_frequency() -> None:
    result = execute_step(
        PlanStep(
            step_id="hourly",
            tool_name="time_series_analysis",
            arguments={
                "date_column": "date",
                "value_column": "revenue",
                "frequency": "hourly",
                "aggregation": "sum",
            },
        ),
        _dataset("time_series.csv"),
        default_registry(),
    )

    assert result.values["code"] == "INVALID_DATA"
    assert result.values["status"] == "failed"
    assert result.sample_size == 0


def test_time_series_analysis_excludes_invalid_rows_with_warnings() -> None:
    result = execute_step(
        PlanStep(
            step_id="invalid-rows",
            tool_name="time_series_analysis",
            arguments={
                "date_column": "date",
                "value_column": "revenue",
                "frequency": "monthly",
                "aggregation": "mean",
            },
        ),
        _dataset("time_series_invalid.csv"),
        default_registry(),
    )

    assert result.sample_size == 2
    assert [point["value"] for point in result.values["series"]] == [10.0, 30.0]
    assert result.values["status"] == "partial"
    assert {warning.code for warning in result.warnings} >= {
        "INVALID_DATA",
        "HIGH_MISSING_RATE",
        "LOW_SAMPLE_SIZE",
    }


def test_default_registry_exposes_time_series_analysis() -> None:
    tool = default_registry().get("time_series_analysis")

    assert tool is not None
    assert tool.phase == "analysis"
