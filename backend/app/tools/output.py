"""Validated execution metadata returned by analysis tools."""

import math

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from backend.app.contracts.models import Artifact, WarningEvent


class ToolOutput(BaseModel):
    """Tool-specific values remain subject to AnalysisResult JSON validation."""

    model_config = ConfigDict(extra="allow")

    __pydantic_extra__: dict[str, JsonValue] = Field(init=False)

    sample_size: int = Field(default=0, ge=0, strict=True)
    artifacts: list[Artifact] = Field(default_factory=list)
    warnings: list[WarningEvent] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_finite_values(self) -> "ToolOutput":
        _validate_finite(self.model_extra or {})
        return self


def _validate_finite(value: JsonValue) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Tool values must contain finite numbers")
    if isinstance(value, dict):
        for item in value.values():
            _validate_finite(item)
    elif isinstance(value, list):
        for item in value:
            _validate_finite(item)
