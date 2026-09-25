"""Dataset inspection tools."""

from pathlib import Path

import pandas as pd
from pydantic import BaseModel

from backend.app.contracts.models import DatasetReference
from backend.app.tools.registry import Tool, ToolRegistry


BACKEND = Path(__file__).resolve().parents[3]
ALLOWED = (
    (BACKEND / "data").resolve(),
    (BACKEND / "tests" / "fixtures").resolve(),
)


class ColumnProfileInput(BaseModel):
    column: str


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


def column_profile(
    dataset: DatasetReference,
    **kwargs: object,
) -> dict:
    frame = pd.read_csv(_csv(dataset.storage_ref))
    column = str(kwargs["column"])

    if column not in frame.columns:
        raise ValueError(f"Unknown column: {column}")

    series = frame[column]
    numeric = pd.to_numeric(series, errors="coerce").dropna()

    return {
        "data_type": str(series.dtype),
        "missing_count": int(series.isna().sum()),
        "unique_count": int(series.nunique()),
        "minimum": float(numeric.min()) if not numeric.empty else None,
        "maximum": float(numeric.max()) if not numeric.empty else None,
        "mean": float(numeric.mean()) if not numeric.empty else None,
        "quantiles": (
            {
                "0.25": float(numeric.quantile(0.25)),
                "0.50": float(numeric.quantile(0.50)),
                "0.75": float(numeric.quantile(0.75)),
            }
            if not numeric.empty
            else None
        ),
        "top_values": [
            {
                "value": str(value),
                "count": int(count),
            }
            for value, count in series.dropna().value_counts().head(10).items()
        ],
        "warnings": [],
    }


COLUMN_PROFILE_TOOL = Tool(
    name="column_profile",
    description=("Return statistics and frequent values for one dataset column."),
    input_model=ColumnProfileInput,
    accepted_dtypes=frozenset(),
    run=column_profile,
)


def inspection_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(COLUMN_PROFILE_TOOL)
    return registry
