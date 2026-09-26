"""Adapters that expose preprocessing tools through the shared workflow registry."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from backend.app.contracts.models import DatasetReference, PlanStep
from backend.app.tools.preprocessing_tools import (
    CANONICAL_TOOL_NAMES,
    SUPPORTED_TYPES,
    TOOL_ARGUMENT_MODELS,
)
from backend.app.tools.registry import Tool, ToolRegistry

TOOL_DESCRIPTIONS = {
    "handle_missing_values": "Drop or impute missing values in selected columns.",
    "remove_duplicates": (
        "Remove duplicate rows using all columns or a selected subset."
    ),
    "change_datatypes": "Convert one or more columns to supported data types.",
    "encode_categorical": "Encode categorical columns as one-hot or ordinal values.",
    "scale_features": "Scale numeric columns using min-max or standard scaling.",
    "filter_rows": "Keep rows matching one or more validated conditions.",
    "select_columns": "Keep a requested ordered subset of dataset columns.",
    "normalize_values": "Normalize text casing, whitespace, or explicit aliases.",
    "handle_outliers": (
        "Clip, null, or drop numeric outliers using IQR or z-score bounds."
    ),
}
NUMERIC_TOOLS = {"scale_features", "handle_outliers"}


def _converted_schema(
    schema: dict[str, Any], arguments: BaseModel
) -> dict[str, Any]:
    updated = {column: dict(info) for column, info in schema.items()}
    conversions = getattr(arguments, "conversions", None)
    if conversions is None:
        conversions = {
            getattr(arguments, "column"): getattr(arguments, "target_type")
        }
    for column, target_type in conversions.items():
        output_type = "float" if target_type == "currency" else target_type
        updated[column]["datatype"] = output_type
    return updated


def _selected_schema(schema: dict[str, Any], arguments: BaseModel) -> dict[str, Any]:
    return {column: schema[column] for column in getattr(arguments, "columns")}


SCHEMA_UPDATERS = {
    "change_datatypes": _converted_schema,
    "select_columns": _selected_schema,
}


def _make_runner(tool_name: str):
    def run(dataset: DatasetReference, **arguments: Any) -> dict[str, Any]:
        # The shared analysis executor adds this parameter to all tool calls.
        arguments.pop("random_state", None)
        step = PlanStep(
            step_id=f"registry_{tool_name}",
            tool_name=tool_name,
            arguments=arguments,
            depends_on=[],
        )
        from .workflow import run_shared_preprocessing

        processed_dataset, report = run_shared_preprocessing(dataset, [step])
        return {
            "processed_dataset": processed_dataset.model_dump(
                mode="json", by_alias=True
            ),
            "preprocessing_report": report.model_dump(mode="json", by_alias=True),
            "sample_size": report.rows_after,
        }

    return run


def register_preprocessing_tools(registry: ToolRegistry) -> ToolRegistry:
    """Register preprocessing schemas and runners in a shared workflow registry."""
    for tool_name in CANONICAL_TOOL_NAMES:
        accepted_dtypes = (
            frozenset({"integer", "float"})
            if tool_name in NUMERIC_TOOLS
            else frozenset({*SUPPORTED_TYPES, "unknown"})
        )
        registry.register(
            Tool(
                name=tool_name,
                description=TOOL_DESCRIPTIONS[tool_name],
                input_model=TOOL_ARGUMENT_MODELS[tool_name],
                accepted_dtypes=accepted_dtypes,
                run=_make_runner(tool_name),
                phase="preprocessing",
                update_schema=SCHEMA_UPDATERS.get(tool_name),
            )
        )
    return registry
