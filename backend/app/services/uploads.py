"""Store an uploaded CSV inside the allowed dataset directory."""

import csv
from collections.abc import Iterator
from io import StringIO
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
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("The CSV must use UTF-8 encoding") from exc
    _check_rows(text)


def _check_rows(text: str) -> None:
    rows = _records(text)
    try:
        header = next(rows, None)
        if header is None:
            raise ValueError("The CSV does not contain a header row")
        if any(not column.strip() for column in header):
            raise ValueError("Every CSV column must have a name")
        if len(set(header)) != len(header):
            raise ValueError("Every CSV column must have a unique name")
        for row in rows:
            if len(row) != len(header):
                raise ValueError("Every CSV row must have the same number of columns")
    except csv.Error as exc:
        raise ValueError(
            "The CSV contains an invalid field or malformed quoted value"
        ) from exc


def _records(text: str) -> Iterator[list[str]]:
    lines = list(StringIO(text, newline=""))
    reader = csv.reader(lines, strict=True)
    start = 0
    for row in reader:
        end = reader.line_num
        if "".join(lines[start:end]).strip():
            yield row
        start = end


def _write(directory: Path, name: str, content: bytes) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_bytes(content)
    return path
