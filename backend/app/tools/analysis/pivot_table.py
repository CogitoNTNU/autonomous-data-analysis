"""Pivot tables over registered datasets."""

from datetime import date, datetime
from typing import Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from backend.app.contracts.models import DatasetReference, WarningEvent
from backend.app.tools.analysis.files import resolve_csv
from backend.app.tools.registry import Tool

AggregationFunction = Literal["count", "mean", "median", "sum", "min", "max", "std"]

MAX_INLINE_ROWS = 1_000
SOURCE = "pivot_table"


class PivotTableInput(BaseModel):
    """Validated arguments accepted by the pivot table tool."""

    model_config = ConfigDict(extra="forbid")

    index: str = Field(min_length=1)
    columns: str = Field(min_length=1)
    values: str = Field(min_length=1)
    function: AggregationFunction


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
        {str(column): _json_value(value) for column, value in row.items()}
        for row in frame.to_dict(orient="records")
    ]


def _warnings(
    frame: pd.DataFrame,
    request: PivotTableInput,
) -> list[WarningEvent]:
    row_count = len(frame)
    warnings: list[WarningEvent] = []

    if row_count == 0:
        return [_warning("INSUFFICIENT_DATA", "dataset contains no rows")]

    if row_count < 30:
        warnings.append(_warning("LOW_SAMPLE_SIZE", f"dataset n={row_count}"))

    missing_rate = float(frame[request.values].isna().mean())
    if missing_rate > 0.2:
        warnings.append(
            _warning(
                "HIGH_MISSING_RATE",
                f"{request.values} missing={missing_rate:.2f}",
            )
        )

    return warnings


def run(dataset: DatasetReference, **kwargs: object) -> dict[str, object]:
    """Create a small JSON-safe pivot table."""
    request = PivotTableInput.model_validate(
        {
            "index": kwargs.get("index"),
            "columns": kwargs.get("columns"),
            "values": kwargs.get("values"),
            "function": kwargs.get("function"),
        }
    )

    frame = pd.read_csv(resolve_csv(dataset.storage_ref))

    pivot = pd.pivot_table(
        frame,
        index=request.index,
        columns=request.columns,
        values=request.values,
        aggfunc=request.function,
        dropna=False,
        observed=True,
    ).reset_index()

    pivot.columns = [str(column) for column in pivot.columns]

    if len(pivot) > MAX_INLINE_ROWS:
        raise ValueError(
            f"pivot table produced {len(pivot)} rows; "
            "artifact-backed output is required"
        )

    return {
        "rows": _records(pivot),
        "row_count": len(pivot),
        "sample_size": len(frame),
        "warnings": _warnings(frame, request),
    }


TOOL = Tool(
    name="pivot_table",
    description=(
        "Create a pivot table using one row index, one column dimension, "
        "and one aggregated value column. "
        "Required: index, columns, values, function."
    ),
    input_model=PivotTableInput,
    accepted_dtypes=frozenset({"integer", "float"}),
    run=run,
)
