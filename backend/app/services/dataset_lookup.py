"""Find an uploaded CSV in this process, or restore it from the request."""

from pathlib import Path

from backend.app.services.uploads import store_named_csv
from backend.app.storage.datasets import create_dataset_reference


def resolve_dataset(
    directory: Path,
    paths: dict[str, Path],
    request: dict[str, object],
) -> Path:
    dataset_id = request.get("dataset_id")
    if not isinstance(dataset_id, str):
        raise ValueError("Unknown dataset")
    stored = paths.get(dataset_id)
    if stored is not None and stored.is_file():
        return stored
    csv = request.get("csv")
    if not isinstance(csv, str):
        raise ValueError("Unknown dataset")
    path = store_named_csv(directory, dataset_id, csv.encode("utf-8"))
    _readable(path)
    paths[dataset_id] = path
    return path


def _readable(path: Path) -> None:
    try:
        create_dataset_reference(path)
    except (OSError, UnicodeError, ValueError):
        path.unlink(missing_ok=True)
        raise
    except Exception as exc:  # noqa: BLE001 - pandas raises its own read errors
        path.unlink(missing_ok=True)
        raise ValueError("The CSV could not be read") from exc
