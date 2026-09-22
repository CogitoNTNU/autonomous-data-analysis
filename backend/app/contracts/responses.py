"""Common agent response envelope with typed, agent-owned updates."""

from typing import Generic, Literal, TypeVar

from pydantic import Field, model_validator

from .errors import AgentError
from .models import ContractModel, NonEmptyString, WarningEvent

UpdatesT = TypeVar("UpdatesT", bound=ContractModel)


class AgentResponse(ContractModel, Generic[UpdatesT]):
    status: Literal["success", "needs_clarification", "error"]
    updates: UpdatesT
    warnings: list[WarningEvent] = Field(default_factory=list)
    error: AgentError | None = None
    clarification_question: NonEmptyString | None = None

    @model_validator(mode="after")
    def validate_status(self) -> "AgentResponse[UpdatesT]":
        if (self.status == "error") != (self.error is not None):
            raise ValueError("Only error status must include an error")
        if (self.status == "needs_clarification") != (
            self.clarification_question is not None
        ):
            raise ValueError(
                "Only needs_clarification must include a clarification_question"
            )
        return self
