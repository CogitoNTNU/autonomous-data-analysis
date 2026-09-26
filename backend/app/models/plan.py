"""Contracts for executable analysis plans."""

from typing import Any

from pydantic import BaseModel, Field


class PlanStep(BaseModel):
    step_id: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)
