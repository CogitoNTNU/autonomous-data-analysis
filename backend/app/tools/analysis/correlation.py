"""Pairwise numeric correlations calculated by a deterministic analysis tool."""

from itertools import combinations
import math
from typing import Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.app.contracts.models import DatasetReference, WarningEvent
from backend.app.tools.analysis.files import resolve_csv
from backend.app.tools.registry import Tool

SOURCE = "correlation_analysis"
CorrelationMethod = Literal["pearson", "spearman"]


class CorrelationInput(BaseModel):
    """Validated arguments for pairwise numeric correlation analysis."""

    model_config = ConfigDict(extra="forbid")

    columns: list[str] = Field(min_length=2)
    method: CorrelationMethod = "pearson"
    threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    min_periods: int = Field(default=2, ge=2)

    @model_validator(mode="after")
    def validate_unique_columns(self) -> "CorrelationInput":
        if len(self.columns) != len(set(self.columns)):
            raise ValueError("columns must be unique")
        return self


def _warning(code: str, message: str) -> WarningEvent:
    return WarningEvent(code=code, message=message, source=SOURCE)


def _column_warnings(frame: pd.DataFrame) -> list[WarningEvent]:
    warnings: list[WarningEvent] = []
    row_count = len(frame)
    if row_count < 30:
        warnings.append(_warning("LOW_SAMPLE_SIZE", f"dataset n={row_count}"))
    for column in frame.columns:
        observed = frame[column].dropna()
        if row_count and len(observed) / row_count < 0.8:
            warnings.append(
                _warning(
                    "HIGH_MISSING_RATE",
                    f"{column} missing={1 - len(observed) / row_count:.2f}",
                )
            )
        if len(observed) and observed.nunique() == 1:
            warnings.append(_warning("CONSTANT_COLUMN", f"{column} constant"))
    return warnings


def _pair(
    frame: pd.DataFrame,
    column_x: str,
    column_y: str,
    request: CorrelationInput,
) -> tuple[dict[str, object], WarningEvent | None]:
    observed = frame[[column_x, column_y]].dropna()
    sample_size = len(observed)
    coefficient: float | None = None
    if (
        sample_size >= request.min_periods
        and observed[column_x].nunique() > 1
        and observed[column_y].nunique() > 1
    ):
        calculated = observed[column_x].corr(observed[column_y], method=request.method)
        if calculated is not None and math.isfinite(float(calculated)):
            coefficient = float(calculated)
    pair = {
        "column_x": column_x,
        "column_y": column_y,
        "coefficient": coefficient,
        "sample_size": sample_size,
    }
    if coefficient is not None:
        return pair, None
    return pair, _warning(
        "INSUFFICIENT_DATA",
        f"Correlation is undefined for {column_x} and {column_y}",
    )


def run(dataset: DatasetReference, **kwargs: object) -> dict[str, object]:
    """Calculate pairwise-complete correlations for selected numeric columns."""
    request = CorrelationInput.model_validate(
        {
            "columns": kwargs.get("columns"),
            "method": kwargs.get("method", "pearson"),
            "threshold": kwargs.get("threshold", 0.7),
            "min_periods": kwargs.get("min_periods", 2),
        }
    )
    frame = pd.read_csv(resolve_csv(dataset.storage_ref), usecols=request.columns)
    numeric = frame.apply(pd.to_numeric, errors="coerce")
    pairs: list[dict[str, object]] = []
    warnings = _column_warnings(numeric)
    for column_x, column_y in combinations(request.columns, 2):
        pair, warning = _pair(numeric, column_x, column_y, request)
        pairs.append(pair)
        if warning is not None:
            warnings.append(warning)
    strong_pairs = [
        pair
        for pair in pairs
        if isinstance(pair["coefficient"], float)
        and abs(pair["coefficient"]) >= request.threshold
    ]
    return {
        "columns": request.columns,
        "method": request.method,
        "threshold": request.threshold,
        "pairs": pairs,
        "strong_pairs": strong_pairs,
        "sample_size": len(frame),
        "warnings": warnings,
    }


TOOL = Tool(
    name="correlation_analysis",
    description=(
        "Calculate pairwise Pearson or Spearman correlation coefficients for "
        "numeric columns and identify pairs whose absolute coefficient meets a "
        "threshold. Use this to assess numeric relationship strength. Required: "
        "columns. Optional: method, threshold, min_periods."
    ),
    input_model=CorrelationInput,
    accepted_dtypes=frozenset({"integer", "float"}),
    run=run,
)
