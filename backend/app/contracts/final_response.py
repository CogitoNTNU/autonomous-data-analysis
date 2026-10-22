"""The answer the Chat agent presents after the critic has reviewed it."""

from pydantic import Field

from .models import ContractModel, NonEmptyString


class FinalResponse(ContractModel):
    text: NonEmptyString
    artifact_ids: list[str] = Field(default_factory=list)
    follow_up_suggestions: list[str] = Field(default_factory=list)


class ChatUpdates(ContractModel):
    final_response: FinalResponse | None = None
