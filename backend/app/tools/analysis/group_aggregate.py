"""Grouped aggregations over registered datasets."""

from datetime import date, datetime
from typing import Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.app.contracts.models import DatasetReference, WarningEvent
from backend.app.tools.analysis.files import resolve_csv
from backend.app.tools.registry import Tool

AggregationFunction = Literal["count", "mean", "median", "sum", "min", "max", "std"]
MAX_INLINE_GROUPS = 1_000
SOURCE = "group_aggregate"


class Aggregation(BaseModel):
    """One named aggregation to calculate for every group."""

    model_config = ConfigDict(extra="forbid")

    column: str = Field(min_length=1)
    function: AggregationFunction
    alias: str = Field(min_length=1)


class GroupAggregateInput(BaseModel):
    """Validated arguments accepted by the group aggregate tool."""

    model_config = ConfigDict(extra="forbid")

    group_by: list[str] = Field(min_length=1)
    aggregations: list[Aggregation] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_names(self) -> "GroupAggregateInput":
        if len(self.group_by) != len(set(self.group_by)):
            raise ValueError("group_by columns must be unique")

        aliases = [aggregation.alias for aggregation in self.aggregations]
        if len(aliases) != len(set(aliases)):
            raise ValueError("aggregation aliases must be unique")

        collisions = sorted(set(self.group_by) & set(aliases))
        if collisions:
            raise ValueError(
                "aggregation aliases conflict with group_by columns: "
                + ", ".join(collisions)
            )
        return self


def _warning(code: str, message: str) -> WarningEvent:
    return WarningEvent(code=code, message=message, source=SOURCE)


def _json_value(value: object) -> object:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    item = getattr(value, "item", None)
    return item() if callable(item) else value


def _records(frame: pd.DataFrame) -> list[dict[str, object]]:
    return [
        {column: _json_value(value) for column, value in row.items()}
        for row in frame.to_dict(orient="records")
    ]


def _missing_warnings(
    frame: pd.DataFrame, request: GroupAggregateInput
) -> list[WarningEvent]:
    row_count = len(frame)
    warnings: list[WarningEvent] = []
    if row_count == 0:
        return [_warning("INSUFFICIENT_DATA", "dataset contains no rows")]
    if row_count < 30:
        warnings.append(_warning("LOW_SAMPLE_SIZE", f"dataset n={row_count}"))

    for column in dict.fromkeys(
        aggregation.column for aggregation in request.aggregations
    ):
        missing_rate = float(frame[column].isna().mean())
        if missing_rate > 0.2:
            warnings.append(
                _warning("HIGH_MISSING_RATE", f"{column} missing={missing_rate:.2f}")
            )

    for column in request.group_by:
        missing_count = int(frame[column].isna().sum())
        if missing_count:
            warnings.append(
                _warning(
                    "MISSING_GROUP_VALUES",
                    f"{column} has {missing_count} missing group value(s); retained as null",
                )
            )
    return warnings


def run(dataset: DatasetReference, **kwargs: object) -> dict[str, object]:
    """Calculate named aggregations and return a small JSON-safe result table."""
    request = GroupAggregateInput.model_validate(
        {
            "group_by": kwargs.get("group_by"),
            "aggregations": kwargs.get("aggregations"),
        }
    )
    frame = pd.read_csv(resolve_csv(dataset.storage_ref))
    named_aggregations = {
        aggregation.alias: pd.NamedAgg(
            column=aggregation.column,
            aggfunc=aggregation.function,
        )
        for aggregation in request.aggregations
    }
    grouped = (
        frame.groupby(request.group_by, dropna=False, sort=True)
        .agg(**named_aggregations)
        .reset_index()
    )
    if len(grouped) > MAX_INLINE_GROUPS:
        raise ValueError(
            f"group aggregate produced {len(grouped)} groups; "
            "artifact-backed output is required"
        )
    return {
        "groups": _records(grouped),
        "group_count": len(grouped),
        "sample_size": len(frame),
        "warnings": _missing_warnings(frame, request),
    }


TOOL = Tool(
    name="group_aggregate",
    description=(
        "Group rows by one or more columns and calculate named count, mean, median, "
        "sum, min, max, or std aggregations. Required: group_by, aggregations."
    ),
    input_model=GroupAggregateInput,
    accepted_dtypes=frozenset({"integer", "float"}),
    run=run,
)
