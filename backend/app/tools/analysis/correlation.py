"""correlation_analysis: pairwise correlations for numeric columns."""

from pathlib import Path
from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field

from backend.app.contracts.models import DatasetReference, WarningEvent
from backend.app.tools.registry import Tool

BACKEND = Path(__file__).resolve().parents[3]
ALLOWED = ((BACKEND / "data").resolve(), (BACKEND / "tests" / "fixtures").resolve())
SRC = "correlation_analysis"


class CorrelationInput(BaseModel):
    columns: list[str] = Field(min_length=2)
    method: Literal["pearson", "spearman"] = "pearson"


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


def _num(value: object) -> float | None:
    return None if value is None or pd.isna(value) else float(value)


def _warn(code: str, message: str) -> WarningEvent:
    return WarningEvent(code=code, message=message, source=SRC)


def run(dataset: DatasetReference, **kwargs: object) -> dict:
    frame = pd.read_csv(_csv(dataset.storage_ref))
    columns = kwargs["columns"]
    method = kwargs.get("method", "pearson")

    numeric = frame[columns].apply(pd.to_numeric, errors="coerce")
    warnings: list[WarningEvent] = []

    for column in columns:
        observed = numeric[column].dropna()

        if len(observed) < 2:
            warnings.append(_warn("INSUFFICIENT_DATA", f"{column} has too few values"))

        if observed.nunique() <= 1:
            warnings.append(_warn("CONSTANT_COLUMN", f"{column} constant"))

        missing_rate = numeric[column].isna().mean()
        if missing_rate > 0.2:
            warnings.append(
                _warn("HIGH_MISSING_RATE", f"{column} missing={missing_rate:.2f}")
            )

    matrix = numeric.corr(method=method)

    correlations: dict[str, dict[str, float | None]] = {}

    for row in matrix.index:
        correlations[row] = {}
        for column in matrix.columns:
            correlations[row][column] = _num(matrix.loc[row, column])

    return {
        "method": method,
        "correlations": correlations,
        "sample_size": len(frame),
        "warnings": warnings,
    }


TOOL = Tool(
    name="correlation_analysis",
    description=(
        "Pairwise correlation analysis for numeric columns. "
        "Required: columns. Optional: method=pearson|spearman."
    ),
    input_model=CorrelationInput,
    accepted_dtypes=frozenset({"integer", "float"}),
    run=run,
)
