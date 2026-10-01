"""descriptive_statistics: numeric summaries. Calculations live in this tool, not in an LLM."""

import pandas as pd
from pydantic import BaseModel, Field

from backend.app.contracts.models import DatasetReference, WarningEvent
from backend.app.tools.analysis.files import resolve_csv
from backend.app.tools.registry import Tool, ToolRegistry

SRC = "descriptive_statistics"


class StatsInput(BaseModel):
    columns: list[str] = Field(min_length=1)


def _num(value: object) -> float | None:
    return None if value is None or pd.isna(value) else float(value)


def _warn(code: str, message: str) -> WarningEvent:
    return WarningEvent(code=code, message=message, source=SRC)


def run(dataset: DatasetReference, **kwargs: object) -> dict:
    frame = pd.read_csv(resolve_csv(dataset.storage_ref))
    rows = len(frame)
    stats: dict[str, dict[str, float | int | None]] = {}
    warnings: list[WarningEvent] = []
    for column in kwargs["columns"]:
        observed = pd.to_numeric(frame[column], errors="coerce").dropna()
        n = int(len(observed))
        rate = (rows - n) / rows if rows else 1.0
        std = float(observed.std(ddof=1)) if n > 1 else None
        stats[column] = {
            "mean": _num(observed.mean()) if n else None,
            "median": _num(observed.median()) if n else None,
            "std": _num(std),
            "min": _num(observed.min()) if n else None,
            "max": _num(observed.max()) if n else None,
            "n": n,
            "missing_rate": rate,
        }
        if n == 0:
            warnings.append(_warn("INSUFFICIENT_DATA", f"{column} empty"))
        elif n < 30:
            warnings.append(_warn("LOW_SAMPLE_SIZE", f"{column} n={n}"))
        if rate > 0.2:
            warnings.append(_warn("HIGH_MISSING_RATE", f"{column} missing={rate:.2f}"))
        if std == 0.0:
            warnings.append(_warn("CONSTANT_COLUMN", f"{column} constant"))
    return {"columns": stats, "sample_size": rows, "warnings": warnings}


TOOL = Tool(
    name="descriptive_statistics",
    description="Mean, median, std, min, max, n for numeric columns. Required: columns.",
    input_model=StatsInput,
    accepted_dtypes=frozenset({"integer", "float"}),
    run=run,
)


def default_registry() -> ToolRegistry:
    from backend.app.tools.analysis.categorical import (
        TOOL as CATEGORICAL_ANALYSIS_TOOL,
    )
    from backend.app.tools.analysis.group_aggregate import (
        TOOL as GROUP_AGGREGATE_TOOL,
    )
    from backend.app.tools.visualization.catalog import register_visualization

    registry = ToolRegistry()
    registry.register(TOOL)
    registry.register(GROUP_AGGREGATE_TOOL)
    registry.register(CATEGORICAL_ANALYSIS_TOOL)
    register_visualization(registry)
    return registry
