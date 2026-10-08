"""Sort dataset rows by one column."""

from datetime import date, datetime

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from backend.app.contracts.models import DatasetReference
from backend.app.tools.analysis.files import resolve_csv
from backend.app.tools.registry import Tool

MAX_INLINE_ROWS = 1_000


class SortResultsInput(BaseModel):
    """Validated arguments accepted by the sort results tool."""

    model_config = ConfigDict(extra="forbid")

    column: str = Field(min_length=1)
    descending: bool = False


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
    request = SortResultsInput.model_validate(
        {
            "column": kwargs.get("column"),
            "descending": kwargs.get("descending", False),
        }
    )
    frame = pd.read_csv(resolve_csv(dataset.storage_ref))

    sorted_frame = frame.sort_values(
        by=request.column,
        ascending=not request.descending,
        na_position="last",
        kind="stable",
    )

    if len(sorted_frame) > MAX_INLINE_ROWS:
        raise ValueError(
            f"sorted result contains {len(sorted_frame)} rows; "
            "artifact-backed output is required"
        )

    return {
        "rows": _records(sorted_frame),
        "row_count": len(sorted_frame),
        "sample_size": len(frame),
        "warnings": [],
    }


TOOL = Tool(
    name="sort_results",
    description=(
        "Sort dataset rows by one column. Required: column. Optional: descending."
    ),
    input_model=SortResultsInput,
    accepted_dtypes=frozenset(),
    run=run,
)
