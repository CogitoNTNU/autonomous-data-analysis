"""Row and column selection tools for CSV datasets."""

from __future__ import annotations

import math
from typing import Any

from .core import MISSING_VALUES, PreprocessingToolError, ToolExecution, require_columns


def remove_duplicates(
    rows: list[dict[str, str]], arguments: dict, fieldnames: list[str] | None = None
) -> ToolExecution:
    columns = arguments.get("subset", arguments.get("columns"))
    if columns is None:
        columns = list(fieldnames or (rows[0] if rows else []))
    if not isinstance(columns, list) or not all(isinstance(column, str) for column in columns):
        raise PreprocessingToolError("columns must be a list of strings")
    require_columns(rows, columns, fieldnames)
    keep = arguments.get("keep", "first")
    if keep not in {"first", "last"}:
        raise PreprocessingToolError("keep must be 'first' or 'last'")
    indexes = range(len(rows)) if keep == "first" else range(len(rows) - 1, -1, -1)
    kept_indexes = set()
    seen = set()
    for index in indexes:
        signature = tuple(rows[index][column] for column in columns)
        if signature not in seen:
            seen.add(signature)
            kept_indexes.add(index)
    unique_rows = [row for index, row in enumerate(rows) if index in kept_indexes]
    removed = len(rows) - len(unique_rows)
    return ToolExecution(
        unique_rows,
        columns,
        removed,
        f"Removed {removed} duplicate rows",
        [],
    )


def _condition_matches(value: str, operator: str, expected: Any) -> bool:
    is_missing = value.strip().lower() in MISSING_VALUES
    if operator == "is_missing":
        return is_missing
    if operator == "not_missing":
        return not is_missing
    if is_missing:
        return False
    if operator in {"eq", "ne"}:
        matches = value == str(expected)
        return matches if operator == "eq" else not matches
    if operator in {"in", "not_in"}:
        matches = value in {str(item) for item in expected}
        return matches if operator == "in" else not matches
    if operator in {"contains", "starts_with", "ends_with"}:
        expected_text = str(expected)
        if operator == "contains":
            return expected_text in value
        if operator == "starts_with":
            return value.startswith(expected_text)
        return value.endswith(expected_text)
    try:
        numeric_value = float(value)
        numeric_expected = float(expected)
    except (TypeError, ValueError) as error:
        raise PreprocessingToolError(
            f"Operator '{operator}' requires numeric column values and threshold"
        ) from error
    if not math.isfinite(numeric_value) or not math.isfinite(numeric_expected):
        raise PreprocessingToolError("Numeric filter values must be finite")
    return {
        "gt": numeric_value > numeric_expected,
        "gte": numeric_value >= numeric_expected,
        "lt": numeric_value < numeric_expected,
        "lte": numeric_value <= numeric_expected,
    }[operator]


def filter_rows(
    rows: list[dict[str, str]], arguments: dict, fieldnames: list[str] | None = None
) -> ToolExecution:
    conditions = arguments["conditions"]
    columns = list(dict.fromkeys(condition["column"] for condition in conditions))
    require_columns(rows, columns, fieldnames)
    combine = arguments.get("combine", "all")
    kept_rows = []
    for row in rows:
        results = [
            _condition_matches(
                row[condition["column"]], condition["operator"], condition.get("value")
            )
            for condition in conditions
        ]
        matches = all(results) if combine == "all" else any(results)
        if matches:
            kept_rows.append(row)
    return ToolExecution(
        kept_rows,
        columns,
        len(rows) - len(kept_rows),
        f"Filtered rows using {len(conditions)} condition(s)",
        [],
    )


def select_columns(
    rows: list[dict[str, str]], arguments: dict, fieldnames: list[str] | None = None
) -> ToolExecution:
    columns = arguments["columns"]
    source_fields = list(fieldnames or (rows[0].keys() if rows else []))
    require_columns(rows, columns, source_fields)
    if len(set(columns)) != len(columns):
        raise PreprocessingToolError("columns must not contain duplicates")
    selected_rows = [{column: row[column] for column in columns} for row in rows]
    changed_rows = len(rows) if columns != source_fields else 0
    return ToolExecution(
        selected_rows,
        list(columns),
        changed_rows,
        f"Selected {len(columns)} column(s)",
        [],
        list(columns),
        columns != source_fields,
    )