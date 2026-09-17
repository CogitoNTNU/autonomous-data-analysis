"""Inspect the example CSV dataset and print a structured summary."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_DATASET = Path(__file__).resolve().parent.parent / "dataset-example" / "penguins.csv"
MISSING_VALUES = {"", "na", "n/a", "null", "none", "nan"}


def _is_missing(value: str) -> bool:
    """Return whether a CSV value should be treated as missing."""
    return value.strip().lower() in MISSING_VALUES


def _infer_datatype(values: list[str]) -> str:
    """Infer a simple datatype from the non-missing values in a column."""
    present_values = [value.strip() for value in values if not _is_missing(value)]

    if not present_values:
        return "unknown"

    try:
        for value in present_values:
            int(value)
        return "integer"
    except ValueError:
        pass

    try:
        for value in present_values:
            float(value)
        return "float"
    except ValueError:
        return "string"


def inspect_dataset(dataset_path: str | Path = DEFAULT_DATASET) -> dict[str, Any]:
    """Read a CSV dataset, print its structure, and return the inspection results."""
    path = Path(dataset_path)
    if not path.is_file():
        raise FileNotFoundError(f"Dataset not found: {path}")

    with path.open(encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames is None:
            raise ValueError(f"Dataset has no header row: {path}")
        rows = list(reader)

    columns = reader.fieldnames
    column_details = {}
    total_missing = 0

    for column in columns:
        values = [row.get(column, "") or "" for row in rows]
        missing_count = sum(_is_missing(value) for value in values)
        total_missing += missing_count
        column_details[column] = {
            "datatype": _infer_datatype(values),
            "missing_values": missing_count,
        }

    row_signatures = [tuple(row.get(column, "") for column in columns) for row in rows]
    duplicate_rows = sum(count - 1 for count in Counter(row_signatures).values() if count > 1)

    result = {
        "dataset": str(path),
        "number_of_columns": len(columns),
        "number_of_rows": len(rows),
        "missing_values": total_missing,
        "duplicate_rows": duplicate_rows,
        "columns": column_details,
    }

    print("\nDATASET INSPECTION")
    print("=" * 50)
    print(f"Dataset          : {path}")
    print(f"Number of columns: {result['number_of_columns']}")
    print(f"Number of rows   : {result['number_of_rows']}")
    print(f"Missing values   : {result['missing_values']}")
    print(f"Duplicate rows   : {result['duplicate_rows']}")
    print("\nCOLUMN DETAILS")
    print("-" * 50)
    print(f"{'Column':<25} {'Datatype':<12} {'Missing':>7}")
    print("-" * 50)
    for column, details in column_details.items():
        print(
            f"{column:<25} {details['datatype']:<12} "
            f"{details['missing_values']:>7}"
        )
    print("=" * 50)

    return result


if __name__ == "__main__":
    inspect_dataset()
