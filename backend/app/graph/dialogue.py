"""Answer a follow-up message or hand a new analysis request to the Planner."""

import logging
from typing import TypedDict

from backend.app.agents.chat.reply import ChatModel, reply_to_message
from backend.app.agents.chat.schema import ChatContext, PresentedArtifact
from backend.app.contracts.dialogue import DialogueTurn
from backend.app.contracts.errors import AgentError
from backend.app.contracts.state import AgentState
from backend.app.core.exceptions import ModelConnectionError, ModelProviderError

from .new_analysis import NewAnalysisUpdate, new_analysis_update

FAILED_REPLY = "I could not answer this message. Please try again."


class DialogueUpdate(TypedDict, total=False):
    dialogue: list[DialogueTurn]
    errors: list[AgentError]


def dialogue_graph_node(
    state: AgentState, model: ChatModel
) -> DialogueUpdate | NewAnalysisUpdate:
    """A failed reply is recorded in the dialogue; the finished analysis stays valid."""
    dialogue = state.get("dialogue", [])
    if not dialogue or dialogue[-1].role != "user":
        raise ValueError("No follow-up message is pending")
    current = state.get("analysis_round", 1)
    try:
        reply = reply_to_message(_context(state, dialogue), model)
    except (ValueError, TimeoutError, ConnectionError, ModelProviderError) as error:
        failure = _failure(error)
        logging.getLogger(__name__).warning(
            "workflow.chat_reply_failed",
            extra={"run_id": state["run_id"], "error_category": failure.code},
        )
        turn = DialogueTurn(
            role="assistant",
            content=failure.message
            if isinstance(error, ModelConnectionError)
            else FAILED_REPLY,
            analysis_round=current,
            failed=True,
        )
        return DialogueUpdate(
            dialogue=[*dialogue, turn], errors=[*state["errors"], failure]
        )
    turn = DialogueTurn(
        role="assistant",
        content=reply.text,
        analysis_round=current,
        referenced_ids=reply.referenced_ids,
        starts_analysis=reply.analysis_request is not None,
    )
    if reply.analysis_request is None:
        return DialogueUpdate(dialogue=[*dialogue, turn])
    return new_analysis_update(state, reply.analysis_request, [*dialogue, turn])


def _context(state: AgentState, dialogue: list[DialogueTurn]) -> ChatContext:
    *history, message = dialogue
    return ChatContext(
        message=message.content,
        dialogue=history,
        conversation_context=state["conversation_context"],
        user_query=state["user_query"],
        plan=state["plan"],
        preprocessing_report=state["preprocessing_report"],
        analysis_execution_report=state["analysis_execution_report"],
        analysis_results=state["analysis_results"],
        artifacts=[
            PresentedArtifact(artifact_id=artifact.artifact_id, type=artifact.type)
            for artifact in state["artifacts"]
        ],
        interpretation=state["interpretation"],
        critique=state["critique"],
        final_answer=state["final_response"],
        revision_history=state["revision_history"],
        warnings=state["warnings"],
    )


def _failure(error: Exception) -> AgentError:
    if isinstance(error, ModelConnectionError):
        code, message = (
            "TOOL_FAILURE",
            (
                "Cannot connect to the model service. If using NTNU/IDUN, "
                "connect to NTNU VPN or the NTNU network, then try again."
            ),
        )
    elif isinstance(error, TimeoutError):
        code, message = "TIMEOUT", "The chat model did not respond in time."
    elif isinstance(error, ConnectionError):
        code, message = "TOOL_FAILURE", "The chat model could not be reached."
    elif isinstance(error, ModelProviderError):
        code, message = "TOOL_FAILURE", "The chat provider rejected the request."
    else:
        code, message = "INVALID_OUTPUT", "The chat reply could not be validated."
    return AgentError(
        code=code,
        message=message,
        source="chat",
        retryable=isinstance(error, (TimeoutError, ConnectionError)),
        details={"reason": "model_connection_failed"}
        if isinstance(error, ModelConnectionError)
        else {},
    )
