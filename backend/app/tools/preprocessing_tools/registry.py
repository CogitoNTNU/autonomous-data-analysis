"""Validated registry for all deterministic preprocessing tools."""

from __future__ import annotations

from typing import Any, Callable

from .cleaning import change_datatypes, convert_types, handle_missing_values, normalize_values
from .core import (
    ChangeDatatypesArguments,
    EncodeCategoricalArguments,
    FilterRowsArguments,
    HandleOutliersArguments,
    MissingValuesArguments,
    NormalizeValuesArguments,
    PreprocessingToolError,
    RemoveDuplicatesArguments,
    ScaleFeaturesArguments,
    SelectColumnsArguments,
    ToolArguments,
    ToolExecution,
)
from .features import encode_categorical, handle_outliers, scale_features
from .row_operations import filter_rows, remove_duplicates, select_columns

ToolCallable = Callable[..., ToolExecution]

TOOL_ARGUMENT_MODELS: dict[str, type[ToolArguments]] = {
    "handle_missing_values": MissingValuesArguments,
    "remove_duplicates": RemoveDuplicatesArguments,
    "change_datatypes": ChangeDatatypesArguments,
    "convert_types": ChangeDatatypesArguments,
    "encode_categorical": EncodeCategoricalArguments,
    "scale_features": ScaleFeaturesArguments,
    "filter_rows": FilterRowsArguments,
    "select_columns": SelectColumnsArguments,
    "normalize_values": NormalizeValuesArguments,
    "handle_outliers": HandleOutliersArguments,
}

CANONICAL_TOOL_NAMES = (
    "handle_missing_values",
    "remove_duplicates",
    "change_datatypes",
    "encode_categorical",
    "scale_features",
    "filter_rows",
    "select_columns",
    "normalize_values",
    "handle_outliers",
)

TOOLS: dict[str, ToolCallable] = {
    "handle_missing_values": handle_missing_values,
    "remove_duplicates": remove_duplicates,
    "change_datatypes": change_datatypes,
    "convert_types": convert_types,
    "encode_categorical": encode_categorical,
    "scale_features": scale_features,
    "filter_rows": filter_rows,
    "select_columns": select_columns,
    "normalize_values": normalize_values,
    "handle_outliers": handle_outliers,
}


def execute_preprocessing_tool(
    tool_name: str,
    rows: list[dict[str, str]],
    fieldnames: list[str],
    arguments: dict[str, Any],
) -> ToolExecution:
    argument_model = TOOL_ARGUMENT_MODELS.get(tool_name)
    tool = TOOLS.get(tool_name)
    if argument_model is None or tool is None:
        raise PreprocessingToolError(f"Unknown preprocessing tool: {tool_name}")

    normalized_arguments = dict(arguments)
    if (
        tool_name == "handle_missing_values"
        and normalized_arguments.get("strategy") == "drop"
    ):
        normalized_arguments["strategy"] = "drop_rows"
    if tool_name in {"change_datatypes", "convert_types"}:
        if "conversions" not in normalized_arguments and {
            "column",
            "target_type",
        }.issubset(normalized_arguments):
            normalized_arguments = {
                "conversions": {
                    normalized_arguments.pop("column"): normalized_arguments.pop("target_type")
                },
                **normalized_arguments,
            }
    if tool_name == "remove_duplicates" and "columns" in normalized_arguments:
        normalized_arguments["subset"] = normalized_arguments.pop("columns")

    try:
        validated = argument_model.model_validate(normalized_arguments)
    except Exception as error:
        raise PreprocessingToolError(
            f"Invalid arguments for preprocessing tool '{tool_name}': {error}"
        ) from error
    validated_arguments = validated.model_dump(exclude_none=True)
    if tool_name == "remove_duplicates" and validated_arguments.get("subset") is None:
        validated_arguments.pop("subset", None)
    return tool(rows, validated_arguments, fieldnames)