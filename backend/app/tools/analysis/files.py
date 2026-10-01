"""Safe file resolution shared by analysis tools."""

from pathlib import Path


BACKEND = Path(__file__).resolve().parents[3]
ALLOWED_DATA_DIRECTORIES = (
    (BACKEND / "data").resolve(),
    (BACKEND / "tests" / "fixtures").resolve(),
)


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
