"""Planner-specific output schemas."""

from __future__ import annotations

from pydantic import ConfigDict, model_validator

from backend.app.contracts.models import ContractModel, NonEmptyString, Plan


class ClarificationRequest(ContractModel):
    question: NonEmptyString


class PlannerOutput(ContractModel):
    model_config = ConfigDict(
        json_schema_extra={
            "oneOf": [
                {
                    "required": ["plan"],
                    "properties": {
                        "plan": {"type": "object"},
                        "clarification": {"type": "null"},
                    },
                },
                {
                    "required": ["clarification"],
                    "properties": {
                        "plan": {"type": "null"},
                        "clarification": {"type": "object"},
                    },
                },
            ]
        }
    )

    plan: Plan | None = None
    clarification: ClarificationRequest | None = None

    @model_validator(mode="after")
    def exactly_one_output(self) -> PlannerOutput:
        if (self.plan is None) == (self.clarification is None):
            raise ValueError("Exactly one of plan or clarification must be provided")

        return self
