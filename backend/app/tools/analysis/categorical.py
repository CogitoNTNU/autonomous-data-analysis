"""categorical_analysis: counts or shares for one column. The dataset stays unchanged."""

from pathlib import Path

import pandas as pd
from pydantic import BaseModel, Field

from backend.app.contracts.models import DatasetReference, WarningEvent
from backend.app.tools.registry import Tool, ToolRegistry

BACKEND = Path(__file__).resolve().parents[3]
ALLOWED = ((BACKEND / "data").resolve(), (BACKEND / "tests" / "fixtures").resolve())
SRC = "categorical_analysis"
DTYPES = frozenset({"string", "integer", "float"})
HIGH_CARDINALITY_SHARE = 0.5
TOP_CATEGORIES = 10
Pair = tuple[str, int]


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
    pairs = _pairs(counts)
    shown = _shown(pairs)
    rate = missing / rows if rows else 1.0
    return {
        "column": spec.column,
        "normalize": spec.normalize,
        "categories": _categories(shown, spec.normalize, n),
        "n_categories": len(pairs),
        "omitted_categories": len(pairs) - len(shown),
        "mode": _mode(pairs),
        "missing_count": missing,
        "missing_rate": rate,
        "sample_size": rows,
        "warnings": _warnings(spec.column, n, len(pairs), rate),
    }


def _pairs(counts: pd.Series) -> list[Pair]:
    pairs = [(str(value), int(count)) for value, count in counts.items()]
    return sorted(pairs, key=lambda item: (-item[1], item[0]))


def _shown(pairs: list[Pair]) -> list[Pair]:
    # over halvparten unike verdier: bare de største gruppene blir med
    observed = sum(count for _, count in pairs)
    if _crowded(len(pairs), observed) and len(pairs) > TOP_CATEGORIES:
        return pairs[:TOP_CATEGORIES]
    return pairs


def _categories(
    pairs: list[Pair], normalize: bool, n: int
) -> list[dict[str, str | int | float]]:
    key = "proportion" if normalize else "count"
    rows: list[dict[str, str | int | float]] = []
    for value, count in pairs:
        amount: int | float = count / n if normalize else count
        rows.append({"value": value, key: amount})
    return rows


def _mode(pairs: list[Pair]) -> list[str]:
    if not pairs:
        return []
    top = pairs[0][1]
    return [value for value, count in pairs if count == top]


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
    if _crowded(n_categories, n):
        message = f"{column} categories={n_categories}"
        warnings.append(_warn("HIGH_CARDINALITY", message))
    return warnings


def _crowded(n_categories: int, n: int) -> bool:
    return n > 0 and n_categories / n > HIGH_CARDINALITY_SHARE


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


def register_categorical(registry: ToolRegistry) -> ToolRegistry:
    if registry.get(TOOL.name) is None:
        registry.register(TOOL)
    return registry


TOOL = Tool(
    name="categorical_analysis",
    description=(
        "Counts or proportions for one column, plus the mode. "
        "High cardinality keeps the largest groups. Required: column, normalize."
    ),
    input_model=CategoricalInput,
    accepted_dtypes=DTYPES,
    run=run,
)
