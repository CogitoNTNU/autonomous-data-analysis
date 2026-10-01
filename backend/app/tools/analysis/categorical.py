"""Frequency analysis for categorical dataset columns."""

from typing import Any

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from backend.app.contracts.models import DatasetReference, WarningEvent
from backend.app.tools.analysis.files import resolve_csv
from backend.app.tools.registry import Tool

MAX_INLINE_CATEGORIES = 1_000
HIGH_CARDINALITY_SHARE = 0.5
TOP_CATEGORIES = 10
SOURCE = "categorical_analysis"
Row = tuple[object, int]


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


def _ordered(series: pd.Series) -> list[Row]:
    counts = series.value_counts(dropna=True, sort=False)
    return sorted(counts.items(), key=lambda item: (-int(item[1]), str(item[0])))


def _crowded(category_count: int, observed_count: int) -> bool:
    return (
        observed_count > 0 and category_count / observed_count > HIGH_CARDINALITY_SHARE
    )


def _shown(ordered: list[Row], observed_count: int) -> list[Row]:
    # over halvparten unike verdier: bare de største gruppene blir med
    if _crowded(len(ordered), observed_count) and len(ordered) > TOP_CATEGORIES:
        return ordered[:TOP_CATEGORIES]
    return ordered


def _categories(shown: list[Row], normalize: bool, observed_count: int) -> list[dict]:
    if normalize:
        return [
            {"value": _json_value(value), "proportion": float(count / observed_count)}
            for value, count in shown
        ]
    return [
        {"value": _json_value(value), "count": int(count)} for value, count in shown
    ]


def _mode(ordered: list[Row]) -> list[object]:
    if not ordered:
        return []
    top = int(ordered[0][1])
    return [_json_value(value) for value, count in ordered if int(count) == top]


def _warnings(
    series: pd.Series, column: str, category_count: int
) -> list[WarningEvent]:
    row_count = len(series)
    missing_count = int(series.isna().sum())
    observed_count = row_count - missing_count
    warnings: list[WarningEvent] = []
    if observed_count == 0:
        return [_warning("INSUFFICIENT_DATA", f"{column} has no observed values")]
    if observed_count < 30:
        warnings.append(_warning("LOW_SAMPLE_SIZE", f"{column} n={observed_count}"))
    if row_count and missing_count / row_count > 0.2:
        warnings.append(
            _warning(
                "HIGH_MISSING_RATE", f"{column} missing={missing_count / row_count:.2f}"
            )
        )
    if category_count == 1:
        warnings.append(_warning("CONSTANT_COLUMN", f"{column} constant"))
    if _crowded(category_count, observed_count):
        warnings.append(
            _warning("HIGH_CARDINALITY", f"{column} categories={category_count}")
        )
    return warnings


def run(dataset: DatasetReference, **kwargs: object) -> dict[str, object]:
    """Count categories or calculate their proportions among observed values."""
    request = CategoricalAnalysisInput.model_validate(
        {"column": kwargs.get("column"), "normalize": kwargs.get("normalize")}
    )
    series = pd.read_csv(resolve_csv(dataset.storage_ref))[request.column]
    return _result(request.column, bool(request.normalize), series)


def _guard_inline(category_count: int, observed_count: int) -> None:
    crowded = _crowded(category_count, observed_count)
    if category_count <= MAX_INLINE_CATEGORIES or crowded:
        return
    raise ValueError(
        f"categorical analysis produced {category_count} categories; "
        "artifact-backed output is required"
    )


def _result(column: str, normalize: bool, series: pd.Series) -> dict[str, object]:
    row_count = len(series)
    missing_count = int(series.isna().sum())
    observed_count = row_count - missing_count
    ordered = _ordered(series)
    category_count = len(ordered)
    _guard_inline(category_count, observed_count)
    shown = _shown(ordered, observed_count)
    return {
        "column": column,
        "categories": _categories(shown, normalize, observed_count),
        "category_count": category_count,
        "omitted_categories": category_count - len(shown),
        "mode": _mode(ordered),
        "observed_count": observed_count,
        "missing_count": missing_count,
        "normalized": normalize,
        "sample_size": row_count,
        "warnings": _warnings(series, column, category_count),
    }


TOOL = Tool(
    name="categorical_analysis",
    description=(
        "Count category values or return their proportions among observed values. "
        "Includes the mode. High cardinality keeps the largest groups. "
        "Required: column, normalize."
    ),
    input_model=CategoricalAnalysisInput,
    accepted_dtypes=frozenset({"boolean", "string"}),
    run=run,
)
