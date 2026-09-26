"""Feature encoding, scaling, and outlier transformations."""

from __future__ import annotations

import math
import re
from typing import Any

from .core import MISSING_VALUES, PreprocessingToolError, ToolExecution, format_number, require_columns


def _category_column_name(column: str, category: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", category.strip()).strip("_").lower()
    return f"{column}__{slug or 'empty'}"


def encode_categorical(
    rows: list[dict[str, str]], arguments: dict, fieldnames: list[str] | None = None
) -> ToolExecution:
    columns = arguments["columns"]
    require_columns(rows, columns, fieldnames)
    strategy = arguments.get("strategy", "one_hot")
    drop_original = arguments.get("drop_original", False)
    source_fields = list(fieldnames or (rows[0].keys() if rows else []))
    new_fields = list(source_fields)
    mappings: dict[str, Any] = {}
    warnings = []

    for column in columns:
        categories = sorted(
            {
                row[column]
                for row in rows
                if row[column].strip().lower() not in MISSING_VALUES
            }
        )
        if not categories:
            warnings.append(f"No non-missing categories found in '{column}'")
        if strategy == "ordinal":
            encoded_column = f"{column}__encoded"
            if encoded_column in new_fields:
                raise PreprocessingToolError(f"Generated column already exists: {encoded_column}")
            mappings[column] = {category: str(index) for index, category in enumerate(categories)}
            new_fields.append(encoded_column)
            if drop_original:
                new_fields.remove(column)
        else:
            category_columns = {
                category: _category_column_name(column, category) for category in categories
            }
            generated = list(category_columns.values())
            if len(set(generated)) != len(generated):
                raise PreprocessingToolError(
                    f"Category names for '{column}' collide after normalization"
                )
            collisions = set(generated) & set(new_fields)
            if collisions:
                raise PreprocessingToolError(
                    f"Generated column already exists: {', '.join(sorted(collisions))}"
                )
            mappings[column] = category_columns
            new_fields.extend(generated)
            if drop_original:
                new_fields.remove(column)

    encoded_rows = []
    changed_rows = 0
    for row in rows:
        updated = row.copy()
        for column in columns:
            if strategy == "ordinal":
                updated[f"{column}__encoded"] = mappings[column].get(row[column], "")
            else:
                for category, encoded_column in mappings[column].items():
                    updated[encoded_column] = "1" if row[column] == category else "0"
            if drop_original:
                updated.pop(column, None)
        changed_rows += updated != row
        encoded_rows.append(updated)

    return ToolExecution(
        encoded_rows,
        columns,
        changed_rows,
        f"Encoded categorical columns using {strategy}: {', '.join(columns)}",
        warnings,
        new_fields,
        new_fields != source_fields,
    )


def scale_features(
    rows: list[dict[str, str]], arguments: dict, fieldnames: list[str] | None = None
) -> ToolExecution:
    columns = arguments["columns"]
    require_columns(rows, columns, fieldnames)
    method = arguments.get("method", "min_max")
    feature_min, feature_max = arguments.get("feature_range", (0.0, 1.0))
    values_by_column: dict[str, list[float | None]] = {}
    warnings = []

    for column in columns:
        values: list[float | None] = []
        for row_number, row in enumerate(rows, start=2):
            value = row[column]
            if value.strip().lower() in MISSING_VALUES:
                values.append(None)
                continue
            try:
                parsed = float(value)
            except ValueError as error:
                raise PreprocessingToolError(
                    f"Column '{column}' contains a non-numeric value on CSV row {row_number}"
                ) from error
            if not math.isfinite(parsed):
                raise PreprocessingToolError(f"Column '{column}' contains a non-finite value")
            values.append(parsed)
        present = [value for value in values if value is not None]
        if not present:
            warnings.append(f"No numeric values available to scale column '{column}'")
        elif max(present) == min(present):
            warnings.append(f"Column '{column}' is constant; scaled values set to zero")
        values_by_column[column] = values

    scaled_rows = []
    changed_rows = 0
    for index, row in enumerate(rows):
        updated = row.copy()
        for column in columns:
            values = values_by_column[column]
            value = values[index]
            present = [item for item in values if item is not None]
            if value is None or not present:
                continue
            if method == "min_max":
                low, high = min(present), max(present)
                scaled = (
                    0.0
                    if high == low
                    else feature_min + (value - low) * (feature_max - feature_min) / (high - low)
                )
            else:
                mean = sum(present) / len(present)
                variance = sum((item - mean) ** 2 for item in present) / len(present)
                deviation = math.sqrt(variance)
                scaled = 0.0 if deviation == 0 else (value - mean) / deviation
            updated[column] = format_number(scaled)
        changed_rows += updated != row
        scaled_rows.append(updated)

    return ToolExecution(
        scaled_rows,
        columns,
        changed_rows,
        f"Scaled features using {method}",
        warnings,
    )


def _quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def handle_outliers(
    rows: list[dict[str, str]], arguments: dict, fieldnames: list[str] | None = None
) -> ToolExecution:
    columns = arguments["columns"]
    require_columns(rows, columns, fieldnames)
    method = arguments.get("method", "iqr")
    strategy = arguments.get("strategy", "clip")
    threshold = float(arguments.get("threshold", 1.5))
    bounds: dict[str, tuple[float, float]] = {}
    warnings = []

    for column in columns:
        values = []
        for row_number, row in enumerate(rows, start=2):
            raw_value = row[column]
            if raw_value.strip().lower() in MISSING_VALUES:
                continue
            try:
                number = float(raw_value)
            except ValueError as error:
                raise PreprocessingToolError(
                    f"Column '{column}' contains a non-numeric value on CSV row {row_number}"
                ) from error
            if not math.isfinite(number):
                raise PreprocessingToolError(f"Column '{column}' contains a non-finite value")
            values.append(number)
        if len(values) < 2:
            warnings.append(f"Too few numeric values to detect outliers in '{column}'")
            continue
        if method == "iqr":
            q1 = _quantile(values, 0.25)
            q3 = _quantile(values, 0.75)
            spread = q3 - q1
            bounds[column] = (q1 - threshold * spread, q3 + threshold * spread)
        else:
            mean = sum(values) / len(values)
            variance = sum((value - mean) ** 2 for value in values) / len(values)
            deviation = math.sqrt(variance)
            if deviation == 0:
                warnings.append(f"Column '{column}' is constant; no outliers detected")
                continue
            bounds[column] = (mean - threshold * deviation, mean + threshold * deviation)

    output_rows = []
    affected_rows = 0
    outlier_count = 0
    for row in rows:
        updated = row.copy()
        row_is_outlier = False
        row_changed = False
        for column, (low, high) in bounds.items():
            raw_value = row[column]
            if raw_value.strip().lower() in MISSING_VALUES:
                continue
            value = float(raw_value)
            if low <= value <= high:
                continue
            outlier_count += 1
            row_is_outlier = True
            if strategy == "clip":
                updated[column] = format_number(min(max(value, low), high))
                row_changed = True
            elif strategy == "null":
                updated[column] = ""
                row_changed = True
        if strategy == "drop_rows" and row_is_outlier:
            affected_rows += 1
            continue
        if row_changed:
            affected_rows += 1
        output_rows.append(updated)

    return ToolExecution(
        output_rows,
        columns,
        affected_rows,
        f"Handled {outlier_count} outlier value(s) using {method}/{strategy}",
        warnings,
    )