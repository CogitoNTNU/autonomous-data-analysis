"""categorical_analysis: counts or shares for one column. The dataset stays unchanged."""

from pathlib import Path

import pandas as pd
from pydantic import BaseModel, Field

from backend.app.contracts.models import DatasetReference, WarningEvent
from backend.app.tools.registry import Tool

BACKEND = Path(__file__).resolve().parents[3]
ALLOWED = ((BACKEND / "data").resolve(), (BACKEND / "tests" / "fixtures").resolve())
SRC = "categorical_analysis"
DTYPES = frozenset({"string", "integer", "float"})


class CategoricalInput(BaseModel):
    column: str = Field(min_length=1)
    normalize: bool


def run(dataset: DatasetReference, **kwargs: object) -> dict[str, object]:
    spec = CategoricalInput.model_validate(
        {"column": kwargs["column"], "normalize": kwargs["normalize"]}
    )
    frame = pd.read_csv(_csv(dataset.storage_ref))
    if spec.column not in frame.columns:
        return _failed("MISSING_COLUMN", f"Unknown column: {spec.column}")
    return _summary(frame, spec)


def _summary(frame: pd.DataFrame, spec: CategoricalInput) -> dict[str, object]:
    rows = len(frame)
    # tomme celler telles ikke som en kategori
    counts = frame[spec.column].dropna().astype("string").value_counts()
    n = int(counts.sum())
    missing = rows - n
    categories = _categories(counts, spec.normalize, n)
    return {
        "column": spec.column,
        "normalize": spec.normalize,
        "categories": categories,
        "n_categories": len(categories),
        "missing_count": missing,
        "missing_rate": missing / rows if rows else 1.0,
        "sample_size": rows,
        "warnings": _warnings(
            spec.column, n, len(categories), missing / rows if rows else 1.0
        ),
    }


def _categories(
    counts: pd.Series, normalize: bool, n: int
) -> list[dict[str, str | int | float]]:
    # største gruppe først; likt antall sorteres på verdien
    pairs = sorted(counts.items(), key=lambda item: (-int(item[1]), str(item[0])))
    key = "proportion" if normalize else "count"
    rows: list[dict[str, str | int | float]] = []
    for value, count in pairs:
        amount: int | float = int(count) / n if normalize else int(count)
        rows.append({"value": str(value), key: amount})
    return rows


def _warnings(
    column: str, n: int, n_categories: int, rate: float
) -> list[WarningEvent]:
    warnings: list[WarningEvent] = []
    if n == 0:
        warnings.append(_warn("INSUFFICIENT_DATA", f"{column} empty"))
    elif n < 30:
        warnings.append(_warn("LOW_SAMPLE_SIZE", f"{column} n={n}"))
    if rate > 0.2:
        warnings.append(_warn("HIGH_MISSING_RATE", f"{column} missing={rate:.2f}"))
    if n_categories == 1:
        warnings.append(_warn("CONSTANT_COLUMN", f"{column} constant"))
    return warnings


def _failed(code: str, message: str) -> dict[str, object]:
    return {
        "error": message,
        "code": code,
        "sample_size": 0,
        "warnings": [_warn(code, message)],
    }


def _warn(code: str, message: str) -> WarningEvent:
    return WarningEvent(code=code, message=message, source=SRC)


def _csv(storage_ref: str) -> Path:
    raw = Path(storage_ref)
    candidates = [raw] if raw.is_absolute() else [root / raw for root in ALLOWED]
    for candidate in candidates:
        path = candidate.resolve()
        if path.is_file() and any(path.is_relative_to(root) for root in ALLOWED):
            return path
    raise FileNotFoundError("dataset not found or not allowed")


TOOL = Tool(
    name="categorical_analysis",
    description="Counts or proportions for one column. Required: column, normalize.",
    input_model=CategoricalInput,
    accepted_dtypes=DTYPES,
    run=run,
)
