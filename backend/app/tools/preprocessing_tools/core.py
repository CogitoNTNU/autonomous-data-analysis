"""Shared contracts and validation helpers for CSV preprocessing tools."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MISSING_VALUES = {"", "na", "n/a", "null", "none", "nan"}
SUPPORTED_TYPES = {"integer", "float", "string", "boolean", "date", "currency"}
SupportedType = Literal[
    "integer", "float", "string", "boolean", "date", "currency"
]
DEFAULT_DATE_FORMATS = [
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%b %d, %Y",
    "%Y/%m/%d",
    "%d-%m-%Y",
    "%Y.%m.%d",
    "%d %b %Y",
    "%d %B %Y",
    "%m/%d/%Y",
]
FILTER_OPERATORS = {
    "eq",
    "ne",
    "gt",
    "gte",
    "lt",
    "lte",
    "in",
    "not_in",
    "contains",
    "starts_with",
    "ends_with",
    "is_missing",
    "not_missing",
}


class PreprocessingToolError(ValueError):
    """Raised when a registered CSV transformation cannot execute."""


@dataclass(frozen=True)
class ToolExecution:
    rows: list[dict[str, str]]
    affected_columns: list[str]
    rows_affected: int
    description: str
    quality_warnings: list[str]
    fieldnames: list[str] | None = None
    changed: bool | None = None


class ToolArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MissingValuesArguments(ToolArguments):
    columns: list[str] | None = None
    strategy: Literal["drop_rows", "mean", "median", "mode", "constant", "fill"] = "drop_rows"
    constant_value: Any = None
    value: Any = None

    @model_validator(mode="after")
    def require_fill_value(self):
        if self.strategy == "constant" and self.constant_value is None:
            raise ValueError("constant strategy requires constant_value")
        if self.strategy == "fill" and self.value is None:
            raise ValueError("fill strategy requires value")
        return self


class RemoveDuplicatesArguments(ToolArguments):
    subset: list[str] | None = None
    columns: list[str] | None = None
    keep: Literal["first", "last"] = "first"

    @model_validator(mode="after")
    def prevent_conflicting_column_lists(self):
        if self.subset is not None and self.columns is not None:
            raise ValueError("Use either subset or columns, not both")
        return self


class ChangeDatatypesArguments(ToolArguments):
    conversions: dict[str, SupportedType] | None = None
    column: str | None = None
    target_type: SupportedType | None = None
    invalid_value_strategy: Literal["error", "null", "drop"] = "error"
    date_formats: list[str] | None = None

    @field_validator("conversions", mode="before")
    @classmethod
    def normalize_conversion_types(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        return {
            column: "date" if target_type == "datetime" else target_type
            for column, target_type in value.items()
        }

    @field_validator("target_type", mode="before")
    @classmethod
    def normalize_target_type(cls, value: object) -> object:
        return "date" if value == "datetime" else value

    @model_validator(mode="after")
    def require_conversions(self):
        if self.conversions is None and not (self.column and self.target_type):
            raise ValueError("Provide conversions or both column and target_type")
        if self.conversions is not None and (self.column or self.target_type):
            raise ValueError("Use conversions or the single-column form, not both")
        return self


class EncodeCategoricalArguments(ToolArguments):
    columns: list[str] = Field(min_length=1)
    strategy: Literal["one_hot", "ordinal"] = "one_hot"
    drop_original: bool = False

    @model_validator(mode="after")
    def validate_unique_columns(self):
        if len(set(self.columns)) != len(self.columns):
            raise ValueError("columns must not contain duplicates")
        return self


class ScaleFeaturesArguments(ToolArguments):
    columns: list[str] = Field(min_length=1)
    method: Literal["min_max", "standard"] = "min_max"
    feature_range: tuple[float, float] = (0.0, 1.0)

    @model_validator(mode="after")
    def validate_feature_range(self):
        if not all(math.isfinite(value) for value in self.feature_range):
            raise ValueError("feature_range values must be finite")
        if self.feature_range[0] >= self.feature_range[1]:
            raise ValueError("feature_range minimum must be less than maximum")
        return self

    @model_validator(mode="after")
    def validate_unique_columns(self):
        if len(set(self.columns)) != len(self.columns):
            raise ValueError("columns must not contain duplicates")
        return self


class FilterCondition(ToolArguments):
    column: str
    operator: str
    value: Any = None

    @model_validator(mode="after")
    def validate_operator_and_value(self):
        if self.operator not in FILTER_OPERATORS:
            raise ValueError(f"Unsupported filter operator: {self.operator}")
        if self.operator in {"is_missing", "not_missing"} and self.value is not None:
            raise ValueError(f"{self.operator} does not take a value")
        if self.operator not in {"is_missing", "not_missing"} and self.value is None:
            raise ValueError(f"{self.operator} requires a value")
        if self.operator in {"in", "not_in"} and not isinstance(self.value, list):
            raise ValueError(f"{self.operator} requires a list value")
        return self


class FilterRowsArguments(ToolArguments):
    conditions: list[FilterCondition] = Field(min_length=1)
    combine: Literal["all", "any"] = "all"


class SelectColumnsArguments(ToolArguments):
    columns: list[str] = Field(min_length=1)


class NormalizeValuesArguments(ToolArguments):
    column: str
    case: Literal["preserve", "lower", "upper", "title"] = "preserve"
    collapse_whitespace: bool = True
    value_map: dict[str, str] = Field(default_factory=dict)


class HandleOutliersArguments(ToolArguments):
    columns: list[str] = Field(min_length=1)
    method: Literal["iqr", "z_score"] = "iqr"
    strategy: Literal["clip", "drop_rows", "null"] = "clip"
    threshold: float = 1.5

    @model_validator(mode="after")
    def validate_threshold(self):
        if not math.isfinite(self.threshold) or self.threshold <= 0:
            raise ValueError("threshold must be greater than zero")
        if len(set(self.columns)) != len(self.columns):
            raise ValueError("columns must not contain duplicates")
        return self


def require_columns(
    rows: list[dict[str, str]], columns: list[str], fieldnames: list[str] | None = None
) -> None:
    available = set(fieldnames or (rows[0].keys() if rows else []))
    unknown = sorted(set(columns) - available)
    if unknown:
        raise PreprocessingToolError(f"Unknown columns: {', '.join(unknown)}")


def format_number(value: float) -> str:
    if not math.isfinite(value):
        raise PreprocessingToolError("Transformation produced a non-finite number")
    return format(value, ".12g")
