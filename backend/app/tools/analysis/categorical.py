"""Frequency analysis for categorical dataset columns."""

from typing import Any

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from backend.app.contracts.models import DatasetReference, WarningEvent
from backend.app.tools.analysis.files import resolve_csv
from backend.app.tools.registry import Tool

MAX_INLINE_CATEGORIES = 1_000
SOURCE = "categorical_analysis"


class CategoricalAnalysisInput(BaseModel):
    """Validated arguments accepted by the categorical analysis tool."""

    model_config = ConfigDict(extra="forbid")

    column: str = Field(min_length=1)
    normalize: bool


def _warning(code: str, message: str) -> WarningEvent:
    return WarningEvent(code=code, message=message, source=SOURCE)


def _json_value(value: object) -> Any:
    item = getattr(value, "item", None)
    return item() if callable(item) else value


def _categories(series: pd.Series, normalize: bool) -> list[dict[str, object]]:
    counts = series.value_counts(dropna=True, sort=False)
    ordered = sorted(
        counts.items(),
        key=lambda item: (-int(item[1]), str(item[0])),
    )
    if normalize:
        observed_count = int(counts.sum())
        return [
            {
                "value": _json_value(value),
                "proportion": float(count / observed_count),
            }
            for value, count in ordered
        ]
    return [
        {"value": _json_value(value), "count": int(count)} for value, count in ordered
    ]


def _warnings(
    row_count: int,
    observed_count: int,
    missing_count: int,
    category_count: int,
    column: str,
) -> list[WarningEvent]:
    warnings: list[WarningEvent] = []
    if observed_count == 0:
        return [_warning("INSUFFICIENT_DATA", f"{column} has no observed values")]
    if observed_count < 30:
        warnings.append(_warning("LOW_SAMPLE_SIZE", f"{column} n={observed_count}"))
    if row_count and missing_count / row_count > 0.2:
        warnings.append(
            _warning(
                "HIGH_MISSING_RATE",
                f"{column} missing={missing_count / row_count:.2f}",
            )
        )
    if category_count == 1:
        warnings.append(_warning("CONSTANT_COLUMN", f"{column} constant"))
    return warnings


def run(dataset: DatasetReference, **kwargs: object) -> dict[str, object]:
    """Count categories or calculate their proportions among observed values."""
    request = CategoricalAnalysisInput.model_validate(
        {"column": kwargs.get("column"), "normalize": kwargs.get("normalize")}
    )
    frame = pd.read_csv(resolve_csv(dataset.storage_ref))
    series = frame[request.column]
    row_count = len(series)
    missing_count = int(series.isna().sum())
    observed_count = row_count - missing_count
    category_count = int(series.nunique(dropna=True))
    if category_count > MAX_INLINE_CATEGORIES:
        raise ValueError(
            f"categorical analysis produced {category_count} categories; "
            "artifact-backed output is required"
        )
    return {
        "column": request.column,
        "categories": _categories(series, request.normalize),
        "category_count": category_count,
        "observed_count": observed_count,
        "missing_count": missing_count,
        "normalized": request.normalize,
        "sample_size": row_count,
        "warnings": _warnings(
            row_count,
            observed_count,
            missing_count,
            category_count,
            request.column,
        ),
    }


TOOL = Tool(
    name="categorical_analysis",
    description=(
        "Count category values or return their proportions among observed values. "
        "Required: column, normalize."
    ),
    input_model=CategoricalAnalysisInput,
    accepted_dtypes=frozenset({"boolean", "string"}),
    run=run,
)
