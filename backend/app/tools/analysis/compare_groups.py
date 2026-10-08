"""Compare a numeric column across groups."""

from datetime import date, datetime

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from backend.app.contracts.models import DatasetReference, WarningEvent
from backend.app.tools.analysis.files import resolve_csv
from backend.app.tools.registry import Tool

MAX_INLINE_GROUPS = 1_000
SOURCE = "compare_groups"


class CompareGroupsInput(BaseModel):
    """Validated arguments accepted by the group comparison tool."""

    model_config = ConfigDict(extra="forbid")

    group_by: str = Field(min_length=1)
    values: str = Field(min_length=1)


def _warning(code: str, message: str) -> WarningEvent:
    return WarningEvent(code=code, message=message, source=SOURCE)


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


def _warnings(
    frame: pd.DataFrame,
    request: CompareGroupsInput,
) -> list[WarningEvent]:
    warnings: list[WarningEvent] = []

    if len(frame) < 30:
        warnings.append(_warning("LOW_SAMPLE_SIZE", f"dataset n={len(frame)}"))

    missing_rate = float(frame[request.values].isna().mean())
    if missing_rate > 0.2:
        warnings.append(
            _warning(
                "HIGH_MISSING_RATE",
                f"{request.values} missing={missing_rate:.2f}",
            )
        )

    return warnings


def run(dataset: DatasetReference, **kwargs: object) -> dict[str, object]:
    request = CompareGroupsInput.model_validate(
        {
            "group_by": kwargs.get("group_by"),
            "values": kwargs.get("values"),
        }
    )
    frame = pd.read_csv(resolve_csv(dataset.storage_ref))

    grouped = (
        frame.groupby(request.group_by, dropna=False, sort=True)[request.values]
        .agg(["count", "mean", "median", "std", "min", "max"])
        .reset_index()
    )

    if len(grouped) > MAX_INLINE_GROUPS:
        raise ValueError(
            f"group comparison produced {len(grouped)} groups; "
            "artifact-backed output is required"
        )

    return {
        "groups": _records(grouped),
        "group_count": len(grouped),
        "sample_size": len(frame),
        "warnings": _warnings(frame, request),
    }


TOOL = Tool(
    name="compare_groups",
    description=(
        "Compare summary statistics for one numeric column across groups. "
        "Required: group_by, values."
    ),
    input_model=CompareGroupsInput,
    accepted_dtypes=frozenset({"integer", "float"}),
    run=run,
)
