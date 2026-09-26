"""CSV access, derived-file writing, and metadata generation."""

from __future__ import annotations

import csv
import hashlib
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

from ...models.dataset import ColumnMetadata, DatasetMetadata
from .core import MISSING_VALUES, PreprocessingToolError


def resolve_dataset_path(uri: str) -> Path:
    path = Path(uri)
    candidates = [
        path,
        Path.cwd() / path,
        Path(__file__).resolve().parents[2] / path,
        Path(__file__).resolve().parents[3] / path,
        Path(__file__).resolve().parents[4] / path,
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"Dataset not found: {uri}")


def load_csv(uri: str) -> tuple[list[str], list[dict[str, str]]]:
    path = resolve_dataset_path(uri)
    with path.open(encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames is None:
            raise PreprocessingToolError(f"Dataset has no header row: {uri}")
        return reader.fieldnames, list(reader)


def write_csv(
    source_uri: str,
    fieldnames: list[str],
    rows: list[dict[str, str]],
) -> tuple[str, str]:
    source = resolve_dataset_path(source_uri)
    with source.open(encoding="utf-8", newline="") as source_file:
        source_content = source_file.read()
    output_hash = hashlib.sha256(
        (source_content + repr(fieldnames) + repr(rows)).encode("utf-8")
    ).hexdigest()
    output = source.with_name(f"{source.stem}.{output_hash[:12]}{source.suffix}")
    with output.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return str(output), output_hash


def build_metadata(fieldnames: list[str], rows: list[dict[str, str]]) -> DatasetMetadata:
    columns = []
    total_missing = 0
    for fieldname in fieldnames:
        values = [row.get(fieldname, "") for row in rows]
        present = [
            value.strip()
            for value in values
            if value.strip().lower() not in MISSING_VALUES
        ]
        datatype = "unknown"
        if present:
            if all(value.lower() in {"true", "false"} for value in present):
                datatype = "boolean"
            else:
                try:
                    [date.fromisoformat(value) for value in present]
                    datatype = "date"
                except ValueError:
                    try:
                        [int(value) for value in present]
                        datatype = "integer"
                    except ValueError:
                        try:
                            [float(value) for value in present]
                            datatype = "float"
                        except ValueError:
                            datatype = "string"
        missing_count = len(values) - len(present)
        total_missing += missing_count
        columns.append(
            ColumnMetadata(
                name=fieldname,
                data_type=datatype,
                nullable=missing_count > 0,
                missing_count=missing_count,
                unique_count=len(set(present)),
                example_values=present[:3],
            )
        )

    signatures = [tuple(row.get(fieldname, "") for fieldname in fieldnames) for row in rows]
    duplicate_count = sum(count - 1 for count in Counter(signatures).values() if count > 1)
    return DatasetMetadata(
        row_count=len(rows),
        column_count=len(fieldnames),
        columns=columns,
        missing_value_count=total_missing,
        duplicate_row_count=duplicate_count,
        created_at=datetime.now(timezone.utc),
    )