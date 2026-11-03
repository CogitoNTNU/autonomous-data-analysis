"""What the Chat agent receives: reviewed results, charts, and follow-up messages."""

from typing import Literal

from pydantic import Field

from backend.app.contracts.dialogue import DialogueTurn
from backend.app.contracts.final_response import FinalResponse
from backend.app.contracts.models import (
    AnalysisExecutionReport,
    AnalysisResult,
    ContractModel,
    ConversationMessage,
    Critique,
    Interpretation,
    NonEmptyString,
    Plan,
    PreprocessingReport,
    RevisionRecord,
    WarningEvent,
)


class PresentedArtifact(ContractModel):
    """An artifact as the browser holds it, without its storage location."""

    artifact_id: NonEmptyString
    type: Literal["figure", "table"]


class ChatInput(ContractModel):
    interpretation: Interpretation
    critique: Critique | None
    figure_ids: list[NonEmptyString]


class ChatContext(ContractModel):
    """Recorded evidence the Chat agent may cite when answering a follow-up."""

    message: NonEmptyString
    dialogue: list[DialogueTurn] = Field(default_factory=list)
    conversation_context: list[ConversationMessage] = Field(default_factory=list)
    user_query: str
    plan: Plan | None = None
    preprocessing_report: PreprocessingReport | None = None
    analysis_execution_report: AnalysisExecutionReport | None = None
    analysis_results: list[AnalysisResult] = Field(default_factory=list)
    artifacts: list[PresentedArtifact] = Field(default_factory=list)
    interpretation: Interpretation | None = None
    critique: Critique | None = None
    final_answer: FinalResponse | None = None
    revision_history: list[RevisionRecord] = Field(default_factory=list)
    warnings: list[WarningEvent] = Field(default_factory=list)
