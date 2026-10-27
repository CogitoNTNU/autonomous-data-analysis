"""LangGraph state schema and per-run initialization (no global state instance)."""

from typing import TypedDict
from uuid import uuid4

from .errors import AgentError
from .final_response import FinalResponse
from .models import (
    AnalysisExecutionReport,
    AnalysisResult,
    Artifact,
    ConversationMessage,
    Critique,
    DatasetReference,
    Interpretation,
    Plan,
    PreprocessingReport,
    RevisionRecord,
    RunControl,
    WarningEvent,
)
from .responses import ResponseStatus


class AgentState(TypedDict):
    run_id: str
    user_query: str
    conversation_context: list[ConversationMessage]
    dataset: DatasetReference
    plan: Plan | None
    processed_dataset: DatasetReference | None
    preprocessing_report: PreprocessingReport | None
    analysis_execution_report: AnalysisExecutionReport | None
    analysis_results: list[AnalysisResult]
    artifacts: list[Artifact]
    interpretation: Interpretation | None
    critique: Critique | None
    final_response: FinalResponse | None
    errors: list[AgentError]
    warnings: list[WarningEvent]
    last_node_status: ResponseStatus | None
    last_node_error: AgentError | None
    revision_history: list[RevisionRecord]
    control: RunControl
    clarification_question: str | None
    clarification_count: int


def create_initial_state(
    user_query: str,
    dataset: DatasetReference,
    *,
    run_id: str | None = None,
    conversation_context: list[ConversationMessage] | None = None,
    max_revisions: int = 2,
    max_retries: int = 2,
) -> AgentState:
    """Create isolated mutable values for each user run."""
    return AgentState(
        run_id=run_id if run_id is not None else str(uuid4()),
        user_query=user_query,
        conversation_context=[
            m.model_copy(deep=True) for m in conversation_context or []
        ],
        dataset=dataset.model_copy(deep=True),
        plan=None,
        processed_dataset=None,
        preprocessing_report=None,
        analysis_execution_report=None,
        analysis_results=[],
        artifacts=[],
        interpretation=None,
        critique=None,
        final_response=None,
        errors=[],
        warnings=[],
        last_node_status=None,
        last_node_error=None,
        revision_history=[],
        control=RunControl(max_revisions=max_revisions, max_retries=max_retries),
        clarification_question=None,
        clarification_count=0,
    )
