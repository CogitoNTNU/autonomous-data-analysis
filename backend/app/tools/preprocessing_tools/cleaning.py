"""Missing-value, normalization, and datatype preprocessing tools."""

from __future__ import annotations

import math
import unicodedata
from collections import Counter
from datetime import datetime
from typing import Any

from .core import (
    DEFAULT_DATE_FORMATS,
    MISSING_VALUES,
    SUPPORTED_TYPES,
    PreprocessingToolError,
    ToolExecution,
    format_number,
    require_columns,
)


def handle_missing_values(
    rows: list[dict[str, str]], arguments: dict, fieldnames: list[str] | None = None
) -> ToolExecution:
    columns = arguments.get("columns")
    strategy = arguments.get("strategy", "drop_rows")
    if columns is None:
        columns = list(fieldnames or (rows[0] if rows else []))
    if not isinstance(columns, list) or not all(isinstance(column, str) for column in columns):
        raise PreprocessingToolError("columns must be a list of strings")
    require_columns(rows, columns, fieldnames)

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

    if strategy not in {"mean", "median", "mode", "constant", "fill"}:
        raise PreprocessingToolError("Unsupported missing-value strategy")

    fill_values: dict[str, str] = {}
    for column in columns:
        observed = [
            row[column].strip()
            for row in rows
            if row[column].strip().lower() not in MISSING_VALUES
        ]
        if strategy == "constant":
            fill_values[column] = str(arguments["constant_value"])
        elif strategy == "fill":
            fill_values[column] = str(arguments["value"])
        elif strategy == "mode":
            if observed:
                fill_values[column] = Counter(observed).most_common(1)[0][0]
        elif observed:
            try:
                numeric = sorted(float(value) for value in observed)
            except ValueError as error:
                raise PreprocessingToolError(
                    f"{strategy} imputation requires numeric values in '{column}'"
                ) from error
            if strategy == "mean":
                fill_values[column] = format_number(sum(numeric) / len(numeric))
            else:
                middle = len(numeric) // 2
                median = (
                    numeric[middle]
                    if len(numeric) % 2
                    else (numeric[middle - 1] + numeric[middle]) / 2
                )
                fill_values[column] = format_number(median)

    changed_rows = 0
    updated_rows = []
    for row in rows:
        updated = row.copy()
        row_changed = False
        for column in columns:
            if updated[column].strip().lower() in MISSING_VALUES and column in fill_values:
                updated[column] = fill_values[column]
                row_changed = True
        changed_rows += row_changed
        updated_rows.append(updated)
    warnings = [
        f"No observed values available to impute column '{column}'"
        for column in columns
        if column not in fill_values
    ]
    return ToolExecution(
        updated_rows,
        columns,
        changed_rows,
        f"Imputed missing values using {strategy} in {', '.join(columns)}",
        warnings,
    )


def parse_numeric_value(value: str) -> float:
    normalized = value.strip()
    negative = normalized.startswith("(") and normalized.endswith(")")
    if negative:
        normalized = normalized[1:-1]
    normalized = "".join(
        character
        for character in normalized
        if not character.isspace() and unicodedata.category(character) != "Sc"
    ).replace("'", "")

    comma = normalized.rfind(",")
    dot = normalized.rfind(".")
    if comma >= 0 and dot >= 0:
        decimal_separator = "," if comma > dot else "."
        thousands_separator = "." if decimal_separator == "," else ","
        normalized = normalized.replace(thousands_separator, "")
        normalized = normalized.replace(decimal_separator, ".")
    elif comma >= 0:
        if len(normalized) - comma - 1 == 3 and normalized.count(",") == 1:
            normalized = normalized.replace(",", "")
        else:
            normalized = normalized.replace(",", ".")
    elif dot >= 0 and normalized.count(".") > 1:
        parts = normalized.split(".")
        normalized = "".join(parts) if len(parts[-1]) == 3 else "".join(parts[:-1]) + "." + parts[-1]
    elif dot >= 0 and len(normalized) - dot - 1 == 3:
        normalized = normalized.replace(".", "")

    number = float(normalized)
    return -number if negative else number


def parse_date_value(value: str, date_formats: list[str] | None) -> str:
    formats = list(dict.fromkeys([*(date_formats or []), *DEFAULT_DATE_FORMATS]))
    for date_format in formats:
        try:
            return datetime.strptime(value.strip(), date_format).date().isoformat()
        except ValueError:
            continue
    raise ValueError("date does not match the supported formats")


def convert_value(value: str, target_type: str, arguments: dict[str, Any]) -> str:
    if target_type not in SUPPORTED_TYPES:
        raise PreprocessingToolError(
            f"Unsupported target type: {target_type}; expected one of {sorted(SUPPORTED_TYPES)}"
        )
    if target_type == "integer":
        return str(int(value))
    if target_type in {"float", "currency"}:
        return format_number(parse_numeric_value(value))
    if target_type == "boolean":
        boolean_values = {
            "true": "true",
            "yes": "true",
            "y": "true",
            "1": "true",
            "active": "true",
            "false": "false",
            "no": "false",
            "n": "false",
            "0": "false",
            "inactive": "false",
        }
        normalized = value.strip().lower()
        if normalized not in boolean_values:
            raise ValueError("value is not a recognized boolean")
        return boolean_values[normalized]
    if target_type == "date":
        return parse_date_value(value, arguments.get("date_formats"))
    return value


def change_datatypes(
    rows: list[dict[str, str]], arguments: dict, fieldnames: list[str] | None = None
) -> ToolExecution:
    conversions = arguments.get("conversions")
    if conversions is None:
        conversions = {arguments["column"]: arguments["target_type"]}
    if not isinstance(conversions, dict) or not conversions:
        raise PreprocessingToolError("conversions must be a non-empty column-to-type mapping")
    require_columns(rows, list(conversions), fieldnames)
    invalid_types = sorted(set(conversions.values()) - SUPPORTED_TYPES)
    if invalid_types:
        raise PreprocessingToolError(f"Unsupported target types: {', '.join(invalid_types)}")

    invalid_strategy = arguments.get("invalid_value_strategy", "error")
    converted_rows = []
    invalid_count = 0
    changed_rows = 0
    dropped_rows = 0
    for row_number, row in enumerate(rows, start=2):
        updated = row.copy()
        invalid_row = False
        for column, target_type in conversions.items():
            value = row[column]
            if value.strip().lower() in MISSING_VALUES:
                continue
            try:
                updated[column] = convert_value(value, target_type, arguments)
            except (ValueError, OverflowError) as error:
                if invalid_strategy == "error":
                    raise PreprocessingToolError(
                        f"Cannot convert column '{column}' value on CSV row {row_number} to {target_type}"
                    ) from error
                invalid_count += 1
                if invalid_strategy == "drop":
                    invalid_row = True
                    break
                updated[column] = ""
        if invalid_row:
            dropped_rows += 1
        else:
            changed_rows += updated != row
            converted_rows.append(updated)

    warnings = []
    if invalid_count and invalid_strategy != "error":
        warnings.append(f"{invalid_count} invalid value(s) handled using '{invalid_strategy}'")
    return ToolExecution(
        converted_rows,
        list(conversions),
        dropped_rows + changed_rows,
        f"Converted datatypes for {', '.join(conversions)}",
        warnings,
    )


def convert_types(
    rows: list[dict[str, str]], arguments: dict, fieldnames: list[str] | None = None
) -> ToolExecution:
    """Compatibility alias for the former single-column conversion tool."""
    return change_datatypes(rows, arguments, fieldnames)


def normalize_values(
    rows: list[dict[str, str]], arguments: dict, fieldnames: list[str] | None = None
) -> ToolExecution:
    column = arguments["column"]
    require_columns(rows, [column], fieldnames)
    case = arguments.get("case", "preserve")
    configured_map = arguments.get("value_map", {})
    value_map = {
        " ".join(source.strip().split()).casefold(): target
        for source, target in configured_map.items()
    }
    for target in configured_map.values():
        canonical_key = " ".join(target.strip().split()).casefold()
        value_map.setdefault(canonical_key, target)

    normalized_rows = []
    changed_rows = 0
    for row in rows:
        updated = row.copy()
        value = updated[column].strip()
        if arguments.get("collapse_whitespace", True):
            value = " ".join(value.split())
        mapped_value = value_map.get(value.casefold())
        if mapped_value is not None:
            value = mapped_value
        elif case == "lower":
            value = value.lower()
        elif case == "upper":
            value = value.upper()
        elif case == "title":
            value = value.title()
        updated[column] = value
        changed_rows += updated != row
        normalized_rows.append(updated)

    return ToolExecution(
        normalized_rows,
        [column],
        changed_rows,
        f"Normalized values in '{column}'",
        [],
    )
