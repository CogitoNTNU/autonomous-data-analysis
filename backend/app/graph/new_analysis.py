"""Start a new analysis round from a follow-up request on the same dataset."""

from typing import TypedDict

from backend.app.contracts.dialogue import MAX_DIALOGUE_MESSAGES, DialogueTurn
from backend.app.contracts.models import (
    AnalysisResult,
    Artifact,
    ConversationMessage,
    RunControl,
    WarningEvent,
)
from backend.app.contracts.state import AgentState


class NewAnalysisUpdate(TypedDict):
    user_query: str
    conversation_context: list[ConversationMessage]
    dialogue: list[DialogueTurn]
    analysis_round: int
    plan: None
    processed_dataset: None
    preprocessing_report: None
    analysis_execution_report: None
    analysis_results: list[AnalysisResult]
    artifacts: list[Artifact]
    interpretation: None
    critique: None
    final_response: None
    warnings: list[WarningEvent]
    last_node_status: None
    last_node_error: None
    clarification_question: None
    clarification_count: int
    control: RunControl


def new_analysis_update(
    state: AgentState, request: str, dialogue: list[DialogueTurn]
) -> NewAnalysisUpdate:
    """Keep the source dataset and conversation; clear every derived output."""
    current = state.get("analysis_round", 1)
    answer = state["final_response"]
    history = [
        *state["conversation_context"],
        ConversationMessage(role="user", content=state["user_query"]),
        *(
            [ConversationMessage(role="assistant", content=answer.text)]
            if answer
            else []
        ),
        *(
            ConversationMessage(role=turn.role, content=turn.content)
            for turn in dialogue
            if turn.analysis_round == current
        ),
    ]
    return NewAnalysisUpdate(
        user_query=request,
        conversation_context=history[-MAX_DIALOGUE_MESSAGES:],
        dialogue=dialogue,
        analysis_round=current + 1,
        plan=None,
        processed_dataset=None,
        preprocessing_report=None,
        analysis_execution_report=None,
        analysis_results=[],
        artifacts=[],
        interpretation=None,
        critique=None,
        final_response=None,
        warnings=[],
        last_node_status=None,
        last_node_error=None,
        clarification_question=None,
        clarification_count=0,
        control=state["control"].model_copy(
            update={
                "status": "running",
                "current_agent": None,
                "revision_count": 0,
                "retry_count": 0,
            }
        ),
    )
