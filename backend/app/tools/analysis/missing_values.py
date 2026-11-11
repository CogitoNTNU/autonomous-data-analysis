"""Read-only missing-value counts for columns of any datatype."""

from pydantic import BaseModel, ConfigDict, Field

from backend.app.contracts.models import DatasetReference
from backend.app.tools.analysis.files import read_frame
from backend.app.tools.registry import Tool


class MissingValuesInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    columns: list[str] = Field(min_length=1)


class MissingColumnSummary(BaseModel):
    missing_count: int
    observed_count: int
    missing_rate: float | None


class MissingValuesOutput(BaseModel):
    columns: dict[str, MissingColumnSummary]
    sample_size: int


def run(dataset: DatasetReference, **kwargs: object) -> dict[str, object]:
    arguments = MissingValuesInput.model_validate({"columns": kwargs.get("columns")})
    frame = read_frame(dataset)
    rows = len(frame)
    summaries = {}
    for column in arguments.columns:
        missing = int(frame[column].isna().sum())
        summaries[column] = MissingColumnSummary(
            missing_count=missing,
            observed_count=rows - missing,
            missing_rate=missing / rows if rows else None,
        )
    return MissingValuesOutput(columns=summaries, sample_size=rows).model_dump()


TOOL = Tool(
    name="missing_values_summary",
    description=(
        "Count missing and observed values and missing rates for columns of any "
        "datatype. Required: columns. Select all columns to identify every column "
        "with missing values. Does not modify data."
    ),
    input_model=MissingValuesInput,
    accepted_dtypes=frozenset(),
    run=run,
)
