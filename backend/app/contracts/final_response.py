"""The answer the Chat agent presents after the critic has reviewed it."""

from pydantic import Field

from .models import ContractModel, Finding, NonEmptyString


class FinalResponse(ContractModel):
    text: NonEmptyString
    findings: list[Finding] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    artifact_ids: list[str] = Field(default_factory=list)
    follow_up_suggestions: list[str] = Field(default_factory=list)


class ChatUpdates(ContractModel):
    final_response: FinalResponse | None = None
