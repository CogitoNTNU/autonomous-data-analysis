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

MAX_PREVIEW_ROWS = 20

class PreviewDataInput(BaseModel):
    columns: list[str] | None = None
    limit: int

class GetMetadataInput(BaseModel):
    pass

class InspectSchemaInput(BaseModel):
    pass

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


def get_metadata(
    dataset: DatasetReference,
    **kwargs: object,
) -> dict:
    frame = pd.read_csv(_csv(dataset.storage_ref))

    row_count = len(frame)
    column_count = len(frame.columns)
    missing_value_count = int(frame.isna().sum().sum())
    duplicate_row_count = int(frame.duplicated().sum())

    columns = []
    for column in frame.columns:
        series = frame[column]
        column_info = {
            "name": column,
            "data_type": str(series.dtype),
            "nullable": bool(series.isna().any()),
            "missing_count": int(series.isna().sum()),
            "unique_count": int(series.nunique()),
            "example_values": series.dropna().head(5).tolist(),

        }
        columns.append(column_info)

    return {
        "row_count": row_count,
        "column_count": column_count,
        "columns": columns,
        "missing_value_count": missing_value_count,
        "duplicate_row_count": duplicate_row_count,
    }


def inspect_schema(
    dataset: DatasetReference,
    **kwargs: object,
) -> dict:
    metadata = get_metadata(dataset)

    return {
        "metadata": metadata,
        "warnings": [],
    }



def preview_data(
    dataset: DatasetReference,
    **kwargs: object,
) -> dict:
    # Reads CSV file
    frame = pd.read_csv(_csv(dataset.storage_ref))

    # Gets input for preview_data
    columns = kwargs.get("columns")
    limit = int(kwargs["limit"])

    if limit < 1 or limit > MAX_PREVIEW_ROWS:
        raise ValueError(
            f"limit must be between 1 and {MAX_PREVIEW_ROWS}"
        )

    if columns is not None:
        missing_columns = [
            col for col in columns
            if col not in frame.columns
        ]

        if missing_columns:
            raise ValueError(f"Unknown columns: {missing_columns}")

        frame = frame[columns]

    preview = frame.head(limit)

    rows = preview.to_dict(orient="records")
    return {
        "rows": rows,
        "returned_rows" : len(rows),
    }


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

PREVIEW_DATA_TOOL = Tool(
    name="preview_data",
    description="Return a small preview of dataset rows.",
    input_model=PreviewDataInput,
    accepted_dtypes=frozenset(),
    run=preview_data,
    phase="inspection",
)

GET_METADATA_TOOL = Tool(
    name="get_metadata",
    description="Return metadata about the dataset.",
    input_model=GetMetadataInput,
    accepted_dtypes=frozenset(),
    run=get_metadata,
    phase="inspection",
)

INSPECT_SCHEMA_TOOL = Tool(
    name="inspect_schema",
    description="Inspect the dataset schema and return metadata and warnings.",
    input_model=InspectSchemaInput,
    accepted_dtypes=frozenset(),
    run=inspect_schema,
    phase="inspection",
)

COLUMN_PROFILE_TOOL = Tool(
    name="column_profile",
    description=("Return statistics and frequent values for one dataset column."),
    input_model=ColumnProfileInput,
    accepted_dtypes=frozenset(),
    run=column_profile,
    phase="inspection",
)


def inspection_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(COLUMN_PROFILE_TOOL)
    registry.register(PREVIEW_DATA_TOOL)
    registry.register(GET_METADATA_TOOL)
    registry.register(INSPECT_SCHEMA_TOOL)
    return registry
