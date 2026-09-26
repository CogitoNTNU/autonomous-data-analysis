"""Registered CSV transformations used by the preprocessing agent."""

from __future__ import annotations

import csv
import hashlib
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from ..models.dataset import ColumnMetadata, DatasetMetadata

MISSING_VALUES = {"", "na", "n/a", "null", "none", "nan"}
SUPPORTED_TYPES = {"integer", "float", "string", "boolean"}


class PreprocessingToolError(ValueError):
    """Raised when a registered preprocessing tool cannot execute."""


@dataclass(frozen=True)
class ToolExecution:
    rows: list[dict[str, str]]
    affected_columns: list[str]
    rows_affected: int
    description: str
    quality_warnings: list[str]


def _require_columns(rows: list[dict[str, str]], columns: list[str]) -> None:
    available = set(rows[0]) if rows else set(columns)
    unknown = sorted(set(columns) - available)
    if unknown:
        raise PreprocessingToolError(f"Unknown columns: {', '.join(unknown)}")


def handle_missing_values(
    rows: list[dict[str, str]], arguments: dict
) -> ToolExecution:
    columns = arguments.get("columns")
    strategy = arguments.get("strategy", "drop_rows")
    if columns is None:
        columns = list(rows[0]) if rows else []
    if not isinstance(columns, list) or not all(isinstance(column, str) for column in columns):
        raise PreprocessingToolError("columns must be a list of strings")
    _require_columns(rows, columns)

    if strategy == "drop_rows":
        kept_rows = [
            row
            for row in rows
            if not any(row[column].strip().lower() in MISSING_VALUES for column in columns)
        ]
        return ToolExecution(
            kept_rows,
            columns,
            len(rows) - len(kept_rows),
            f"Dropped rows containing missing values in {', '.join(columns)}",
            [],
        )

    if strategy == "fill":
        if "value" not in arguments:
            raise PreprocessingToolError("fill strategy requires a value")
        value = str(arguments["value"])
        changed = 0
        updated_rows = []
        for row in rows:
            updated = row.copy()
            for column in columns:
                if updated[column].strip().lower() in MISSING_VALUES:
                    updated[column] = value
                    changed += 1
            updated_rows.append(updated)
        return ToolExecution(
            updated_rows,
            columns,
            changed,
            f"Filled missing values in {', '.join(columns)}",
            [],
        )

    raise PreprocessingToolError(
        "Unsupported missing-value strategy; expected 'drop_rows' or 'fill'"
    )


def convert_types(rows: list[dict[str, str]], arguments: dict) -> ToolExecution:
    column = arguments.get("column")
    target_type = arguments.get("target_type")
    if not isinstance(column, str) or not isinstance(target_type, str):
        raise PreprocessingToolError("type conversion requires column and target_type")
    _require_columns(rows, [column])
    if target_type not in SUPPORTED_TYPES:
        raise PreprocessingToolError(
            f"Unsupported target_type: {target_type}; expected one of {sorted(SUPPORTED_TYPES)}"
        )

    converted_rows = []
    for row_number, row in enumerate(rows, start=2):
        value = row[column]
        if value.strip().lower() in MISSING_VALUES:
            converted_rows.append(row.copy())
            continue
        try:
            if target_type == "integer":
                converted = str(int(value))
            elif target_type == "float":
                converted = str(float(value))
            elif target_type == "boolean":
                normalized = value.strip().lower()
                if normalized not in {"true", "false"}:
                    raise ValueError
                converted = normalized
            else:
                converted = value
        except ValueError as error:
            raise PreprocessingToolError(
                f"Cannot convert column '{column}' value on CSV row {row_number} to {target_type}"
            ) from error
        updated = row.copy()
        updated[column] = converted
        converted_rows.append(updated)

    return ToolExecution(
        converted_rows,
        [column],
        len(rows),
        f"Converted column '{column}' to {target_type}",
        [],
    )


def remove_duplicates(rows: list[dict[str, str]], arguments: dict) -> ToolExecution:
    columns = arguments.get("columns")
    if columns is None:
        columns = list(rows[0]) if rows else []
    if not isinstance(columns, list) or not all(isinstance(column, str) for column in columns):
        raise PreprocessingToolError("columns must be a list of strings")
    _require_columns(rows, columns)

    seen = set()
    unique_rows = []
    for row in rows:
        signature = tuple(row[column] for column in columns)
        if signature not in seen:
            seen.add(signature)
            unique_rows.append(row)
    removed = len(rows) - len(unique_rows)
    return ToolExecution(
        unique_rows,
        columns,
        removed,
        f"Removed {removed} duplicate rows",
        [],
    )


TOOLS: dict[str, Callable[[list[dict[str, str]], dict], ToolExecution]] = {
    "handle_missing_values": handle_missing_values,
    "convert_types": convert_types,
    "remove_duplicates": remove_duplicates,
}


def resolve_dataset_path(uri: str) -> Path:
    path = Path(uri)
    candidates = [
        path,
        Path.cwd() / path,
        Path(__file__).resolve().parents[2] / path,
        Path(__file__).resolve().parents[3] / path,
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
        present = [value.strip() for value in values if value.strip().lower() not in MISSING_VALUES]
        datatype = "unknown"
        if present:
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