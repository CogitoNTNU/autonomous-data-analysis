"""Read chart datasets from the approved backend folders."""

from pathlib import Path

import pandas as pd

from backend.app.contracts.models import DatasetReference

BACKEND = Path(__file__).resolve().parents[3]
# samme mapper som descriptive får lese fra
ALLOWED = ((BACKEND / "data").resolve(), (BACKEND / "tests" / "fixtures").resolve())
DEFAULT_ARTIFACTS = BACKEND / "data" / "artifacts"
SOURCE = "visualization"


def runtime_source_rows(
    kwargs: dict[str, object],
) -> list[dict[str, object]] | None:
    rows = kwargs.get("_source_rows")
    if rows is None:
        return None
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError("invalid visualization source rows")
    return rows


def dataset_path(storage_ref: str) -> Path:
    raw = Path(storage_ref)
    candidates = [raw] if raw.is_absolute() else [root / raw for root in ALLOWED]
    for candidate in candidates:
        path = candidate.resolve()
        if path.is_file() and any(path.is_relative_to(root) for root in ALLOWED):
            return path
    raise FileNotFoundError("dataset not found or not allowed")


def read_dataset(
    dataset: DatasetReference,
    source_rows: list[dict[str, object]] | None = None,
) -> pd.DataFrame:
    if source_rows is not None:
        return pd.DataFrame.from_records(source_rows)
    return pd.read_csv(dataset_path(dataset.storage_ref))


def prepare_numeric(
    dataset: DatasetReference,
    columns: list[str],
    source_rows: list[dict[str, object]] | None = None,
) -> pd.DataFrame | dict[str, object]:
    frame = read_dataset(dataset, source_rows)
    if len(frame) == 0:
        return failed("INSUFFICIENT_DATA", "no rows")
    converted = frame.copy()
    for column in columns:
        values = pd.to_numeric(converted[column], errors="coerce")
        if int(values.notna().sum()) == 0:
            return failed("INVALID_DATA", f"{column} is not numeric")
        converted[column] = values
    return converted


def failed(code: str, message: str) -> dict[str, object]:
    warning = {"code": code, "message": message, "source": SOURCE}
    return {"error": message, "code": code, "sample_size": 0, "warnings": [warning]}
