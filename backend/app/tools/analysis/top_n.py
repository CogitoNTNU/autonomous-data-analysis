"""Return the top N dataset rows by one column."""

from datetime import date, datetime

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from backend.app.contracts.models import DatasetReference
from backend.app.tools.analysis.files import resolve_csv
from backend.app.tools.registry import Tool

MAX_INLINE_ROWS = 1_000


class TopNInput(BaseModel):
    """Validated arguments accepted by the top N tool."""

    model_config = ConfigDict(extra="forbid")

    column: str = Field(min_length=1)
    n: int = Field(default=10, ge=1, le=MAX_INLINE_ROWS)
    descending: bool = True


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


def run(dataset: DatasetReference, **kwargs: object) -> dict[str, object]:
    request = TopNInput.model_validate(
        {
            "column": kwargs.get("column"),
            "n": kwargs.get("n", 10),
            "descending": kwargs.get("descending", True),
        }
    )
    frame = pd.read_csv(resolve_csv(dataset.storage_ref))

    selected = frame.sort_values(
        by=request.column,
        ascending=not request.descending,
        na_position="last",
        kind="stable",
    ).head(request.n)

    return {
        "rows": _records(selected),
        "row_count": len(selected),
        "sample_size": len(frame),
        "warnings": [],
    }


TOOL = Tool(
    name="top_n",
    description=(
        "Return the first N rows after sorting by one column. "
        "Required: column. Optional: n, descending."
    ),
    input_model=TopNInput,
    accepted_dtypes=frozenset(),
    run=run,
)
