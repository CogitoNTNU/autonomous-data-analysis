"""What the Chat agent receives: the reviewed interpretation and its charts."""

from typing import Literal

from backend.app.contracts.models import (
    ContractModel,
    Critique,
    Interpretation,
    NonEmptyString,
)


class PresentedArtifact(ContractModel):
    """An artifact as the browser holds it, without its storage location."""

    artifact_id: NonEmptyString
    type: Literal["figure", "table"]


class ChatInput(ContractModel):
    interpretation: Interpretation
    critique: Critique | None
    figure_ids: list[NonEmptyString]
