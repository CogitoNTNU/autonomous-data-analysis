"""Safe file resolution shared by analysis tools."""

from pathlib import Path

import pandas as pd

from backend.app.contracts.models import DatasetReference

from backend.app.storage.datasets import HOSTED_UPLOADS

BACKEND = Path(__file__).resolve().parents[3]
ALLOWED_DATA_DIRECTORIES = (
    (BACKEND / "data").resolve(),
    (BACKEND / "tests" / "fixtures").resolve(),
    HOSTED_UPLOADS.resolve(),
)


def read_frame(
    dataset: DatasetReference, *, columns: list[str] | None = None
) -> pd.DataFrame:
    """Preserve declared text columns rather than inferring numeric categories."""
    dtypes = {
        name: "string"
        for name, info in dataset.dataset_schema.items()
        if isinstance(info, dict)
        and info.get("datatype") in {"string", "date"}
        and (columns is None or name in columns)
    }
    return pd.read_csv(resolve_csv(dataset.storage_ref), dtype=dtypes, usecols=columns)


def resolve_csv(storage_ref: str) -> Path:
    """Resolve a dataset reference without allowing arbitrary file access."""
    raw = Path(storage_ref)
    candidates = (
        [raw]
        if raw.is_absolute()
        else [root / raw for root in ALLOWED_DATA_DIRECTORIES] + [BACKEND / raw]
    )
    for candidate in candidates:
        path = candidate.resolve()
        if path.is_file() and any(
            path.is_relative_to(root) for root in ALLOWED_DATA_DIRECTORIES
        ):
            return path
    raise FileNotFoundError("dataset not found or not allowed")
