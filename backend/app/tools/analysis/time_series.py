"""Aggregate a numeric value column into validated calendar periods."""

from pathlib import Path
from typing import Literal, Self

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.app.contracts.models import DatasetReference, WarningEvent
from backend.app.tools.registry import Tool

BACKEND = Path(__file__).resolve().parents[3]
ALLOWED = ((BACKEND / "data").resolve(), (BACKEND / "tests" / "fixtures").resolve())
SOURCE = "time_series_analysis"
MAX_SERIES_POINTS = 1_000

Frequency = Literal["daily", "weekly", "monthly", "quarterly", "yearly"]
Aggregation = Literal["sum", "mean", "median", "min", "max", "count"]

PERIOD_RULES: dict[Frequency, str] = {
    "daily": "D",
    "weekly": "W-SUN",
    "monthly": "M",
    "quarterly": "Q-DEC",
    "yearly": "Y-DEC",
}


class TimeSeriesInput(BaseModel):
    """Validated arguments described by ``cogito.txt`` section 7."""

    model_config = ConfigDict(extra="forbid")

    date_column: str = Field(min_length=1)
    value_column: str = Field(min_length=1)
    frequency: Frequency
    aggregation: Aggregation

    @property
    def columns(self) -> list[str]:
        """Expose referenced columns to the shared registry validator."""

        return [self.date_column, self.value_column]

    @model_validator(mode="after")
    def validate_distinct_columns(self) -> Self:
        if self.date_column == self.value_column:
            raise ValueError("date_column and value_column must be different")
        return self


class TimeSeriesPoint(BaseModel):
    period: str
    period_start: str
    period_end: str
    value: int | float
    observation_count: int = Field(ge=1)


class TimeSeriesOutput(BaseModel):
    frequency: Frequency
    aggregation: Aggregation
    start_date: str | None
    end_date: str | None
    series: list[TimeSeriesPoint]
    sample_size: int = Field(ge=0)
    warnings: list[WarningEvent]


def _csv(storage_ref: str) -> Path:
    raw = Path(storage_ref)
    candidates = (
        [raw]
        if raw.is_absolute()
        else [root / raw for root in ALLOWED] + [BACKEND / raw]
    )
    for candidate in candidates:
        path = candidate.resolve()
        if path.is_file() and any(path.is_relative_to(root) for root in ALLOWED):
            return path
    raise FileNotFoundError("dataset not found or not allowed")


def _warning(code: str, message: str) -> WarningEvent:
    return WarningEvent(code=code, message=message, source=SOURCE)


def _quality_warnings(
    row_count: int,
    sample_size: int,
    unusable_dates: int,
    unusable_values: int,
) -> list[WarningEvent]:
    warnings: list[WarningEvent] = []
    if unusable_dates:
        warnings.append(
            _warning(
                "INVALID_DATA",
                f"Excluded {unusable_dates} rows with missing or invalid dates",
            )
        )
    if unusable_values:
        warnings.append(
            _warning(
                "INVALID_DATA",
                f"Excluded {unusable_values} rows with missing or non-numeric values",
            )
        )
    if sample_size == 0:
        warnings.append(_warning("INSUFFICIENT_DATA", "No usable observations"))
    elif sample_size < 30:
        warnings.append(_warning("LOW_SAMPLE_SIZE", f"time series n={sample_size}"))
    excluded_rate = (row_count - sample_size) / row_count if row_count else 1.0
    if excluded_rate > 0.2:
        warnings.append(
            _warning(
                "HIGH_MISSING_RATE",
                f"Excluded {excluded_rate:.0%} of rows from the time series",
            )
        )
    return warnings


def _aggregate(values: pd.Series, aggregation: Aggregation) -> int | float:
    if aggregation == "count":
        return int(values.count())
    operation = getattr(values, aggregation)
    return float(operation())


def _points(
    frame: pd.DataFrame,
    request: TimeSeriesInput,
) -> list[TimeSeriesPoint]:
    grouped = frame.groupby("period", sort=True)["value"]
    points: list[TimeSeriesPoint] = []
    for period, values in grouped:
        points.append(
            TimeSeriesPoint(
                period=str(period),
                period_start=period.start_time.date().isoformat(),
                period_end=period.end_time.date().isoformat(),
                value=_aggregate(values, request.aggregation),
                observation_count=int(values.count()),
            )
        )
    return points


def _failed(message: str, sample_size: int) -> dict[str, object]:
    warning = _warning("INVALID_DATA", message)
    return {
        "error": message,
        "code": warning.code,
        "sample_size": sample_size,
        "warnings": [warning],
    }


def run(dataset: DatasetReference, **kwargs: object) -> dict[str, object]:
    """Parse, periodize, and aggregate a time series without mutating its CSV."""

    arguments = {key: value for key, value in kwargs.items() if key != "random_state"}
    request = TimeSeriesInput.model_validate(arguments)
    frame = pd.read_csv(_csv(dataset.storage_ref))

    dates = pd.to_datetime(
        frame[request.date_column], format="mixed", errors="coerce", utc=True
    ).dt.tz_convert(None)
    values = pd.to_numeric(frame[request.value_column], errors="coerce")
    values = values.where(values.abs().ne(float("inf")))
    valid = dates.notna() & values.notna()
    sample_size = int(valid.sum())
    warnings = _quality_warnings(
        len(frame),
        sample_size,
        int(dates.isna().sum()),
        int(values.isna().sum()),
    )

    usable = pd.DataFrame(
        {
            "date": dates.loc[valid],
            "value": values.loc[valid],
        }
    )
    usable["period"] = usable["date"].dt.to_period(PERIOD_RULES[request.frequency])

    if int(usable["period"].nunique()) > MAX_SERIES_POINTS:
        return _failed(
            f"Time series exceeds the {MAX_SERIES_POINTS} point limit; "
            "choose a coarser frequency",
            sample_size,
        )

    points = _points(usable, request) if sample_size else []
    output = TimeSeriesOutput(
        frequency=request.frequency,
        aggregation=request.aggregation,
        start_date=(usable["date"].min().date().isoformat() if sample_size else None),
        end_date=(usable["date"].max().date().isoformat() if sample_size else None),
        series=points,
        sample_size=sample_size,
        warnings=warnings,
    )
    payload = output.model_dump(exclude={"warnings"})
    payload["warnings"] = output.warnings
    return payload


TOOL = Tool(
    name="time_series_analysis",
    description=(
        "Aggregate a numeric value by daily, weekly, monthly, quarterly, or yearly "
        "periods using sum, mean, median, min, max, or count. Required: "
        "date_column, value_column, frequency, aggregation."
    ),
    input_model=TimeSeriesInput,
    accepted_dtypes=frozenset({"date", "string", "integer", "float"}),
    run=run,
)
