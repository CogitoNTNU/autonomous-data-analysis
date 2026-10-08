"""Value counts for a dataset column."""

from typing import Any

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from backend.app.contracts.models import DatasetReference
from backend.app.tools.analysis.files import resolve_csv
from backend.app.tools.registry import Tool


class ValueCountsInput(BaseModel):
    """Validated arguments accepted by the value counts tool."""

    model_config = ConfigDict(extra="forbid")

    column: str = Field(min_length=1)
    dropna: bool = True


def _json_value(value: object) -> Any:
    item = getattr(value, "item", None)
    return item() if callable(item) else value


def run(dataset: DatasetReference, **kwargs: object) -> dict[str, object]:
    request = ValueCountsInput.model_validate(
        {
            "column": kwargs.get("column"),
            "dropna": kwargs.get("dropna", True),
        }
    )
    frame = pd.read_csv(resolve_csv(dataset.storage_ref))
    counts = frame[request.column].value_counts(
        dropna=request.dropna,
        sort=True,
    )

    values = [
        {"value": _json_value(value), "count": int(count)}
        for value, count in counts.items()
    ]

    return {
        "column": request.column,
        "values": values,
        "unique_count": len(values),
        "sample_size": len(frame),
        "warnings": [],
    }


TOOL = Tool(
    name="value_counts",
    description=(
        "Count occurrences of each distinct value in one column. "
        "Required: column. Optional: dropna."
    ),
    input_model=ValueCountsInput,
    accepted_dtypes=frozenset(),
    run=run,
)
