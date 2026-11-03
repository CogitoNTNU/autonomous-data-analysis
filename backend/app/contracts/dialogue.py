"""Follow-up conversation after an analysis: stored turns and chat replies."""

from typing import Literal

from pydantic import Field, model_validator

from .models import ContractModel, NonEmptyString

MAX_DIALOGUE_MESSAGES = 20


class DialogueTurn(ContractModel):
    role: Literal["user", "assistant"]
    content: NonEmptyString
    analysis_round: int = Field(ge=1)
    referenced_ids: list[NonEmptyString] = Field(default_factory=list)
    starts_analysis: bool = False
    failed: bool = False


class ChatReply(ContractModel):
    """Either answer from the recorded analysis or ask the harness for a new one."""

    action: Literal["answer", "new_analysis"]
    text: NonEmptyString
    referenced_ids: list[NonEmptyString] = Field(default_factory=list)
    analysis_request: NonEmptyString | None = None

    @model_validator(mode="after")
    def validate_request(self) -> "ChatReply":
        if (self.action == "new_analysis") != (self.analysis_request is not None):
            raise ValueError("analysis_request is required only for new_analysis")
        return self
