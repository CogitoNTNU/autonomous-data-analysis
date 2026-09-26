"""Dataset loading and reference creation."""

from pathlib import Path

import pandas as pd

from backend.app.contracts.models import DatasetReference


BACKEND = Path(__file__).resolve().parents[2]
ALLOWED = (
    (BACKEND / "data").resolve(),
    (BACKEND / "tests" / "fixtures").resolve(),
)


def _csv(dataset_path: str | Path) -> Path:
    path = Path(dataset_path)

    if not path.is_absolute():
        path = (BACKEND / path).resolve()
    else:
        path = path.resolve()

    if not path.is_file():
        raise FileNotFoundError(f"Dataset not found: {path}")

    if not any(path.is_relative_to(root) for root in ALLOWED):
        raise ValueError("Dataset is outside the allowed directories")

    return path


def _datatype(series: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(series):
        return "boolean"

    if pd.api.types.is_integer_dtype(series):
        return "integer"

    if pd.api.types.is_float_dtype(series):
        return "float"

    return "string"


def create_dataset_reference(
    dataset_path: str | Path,
    *,
    version: str = "raw-v1",
) -> DatasetReference:
    path = _csv(dataset_path)
    frame = pd.read_csv(path)

    schema = {
        column: {
            "datatype": _datatype(frame[column]),
            "missing_count": int(frame[column].isna().sum()),
        }
        for column in frame.columns
    }

    return DatasetReference(
        dataset_id=path.stem,
        version=version,
        storage_ref=str(path),
        schema=schema,
    )
