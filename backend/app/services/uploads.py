"""Store an uploaded CSV inside the allowed dataset directory."""

from pathlib import Path
from uuid import UUID, uuid4

MAX_CSV_BYTES = 10 * 1024 * 1024


def save_csv(directory: Path, content: bytes) -> Path:
    _checked(content)
    return _write(directory, f"{uuid4()}.csv", content)


def store_named_csv(directory: Path, dataset_id: str, content: bytes) -> Path:
    _dataset_id(dataset_id)
    _checked(content)
    return _write(directory, f"{dataset_id}.csv", content)


def _dataset_id(dataset_id: str) -> None:
    try:
        parsed = UUID(dataset_id)
    except ValueError as exc:
        raise ValueError("Unknown dataset") from exc
    if str(parsed) != dataset_id:
        raise ValueError("Unknown dataset")


def _checked(content: bytes) -> None:
    if not content.strip():
        raise ValueError("The CSV is empty")
    if len(content) > MAX_CSV_BYTES:
        raise ValueError("The CSV is larger than 10 MB")


def _write(directory: Path, name: str, content: bytes) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_bytes(content)
    return path
