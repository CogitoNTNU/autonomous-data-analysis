"""Common error codes and diagnostics for agents and tools."""

from typing import Literal

from pydantic import Field, JsonValue

from .models import ContractModel, NonEmptyString

ErrorCode = Literal[
    "MISSING_COLUMN",
    "INVALID_DATA",
    "INSUFFICIENT_DATA",
    "INVALID_OUTPUT",
    "TOOL_FAILURE",
    "TIMEOUT",
    "REVISION_LIMIT",
]


class AgentError(ContractModel):
    code: ErrorCode
    message: NonEmptyString
    source: NonEmptyString
    step_id: str | None = None
    retryable: bool = False
    details: dict[str, JsonValue] = Field(default_factory=dict)
