"""Resolve registered uploads without accepting replacement data from the browser."""

from pathlib import Path
from uuid import UUID

from backend.app.contracts.models import DatasetReference
from backend.app.storage.datasets import create_dataset_reference


def workflow_dataset(directory: Path, dataset_id: UUID) -> DatasetReference:
    path = directory / f"{dataset_id}.csv"
    if not path.is_file():
        raise ValueError("Unknown dataset. Upload the CSV before starting an analysis.")
    return create_dataset_reference(path)
