"""User clarification and final presentation are resumable LangGraph nodes."""

from typing import TypedDict

from langgraph.types import interrupt
from pydantic import BaseModel, Field

from backend.app.agents.chat import ChatInput, run_chat
from backend.app.contracts.errors import AgentError
from backend.app.contracts.final_response import ChatUpdates
from backend.app.contracts.models import ConversationMessage, PlannerUpdates
from backend.app.contracts.responses import AgentResponse
from backend.app.contracts.state import AgentState

from .responses import AgentStateUpdate, translate_agent_response


class ClarificationAnswer(BaseModel):
    answer: str = Field(min_length=1, max_length=10000)


class ClarificationUpdate(TypedDict):
    user_query: str
    conversation_context: list[ConversationMessage]
    clarification_question: None
    clarification_count: int


def clarify(state: AgentState) -> ClarificationUpdate | AgentStateUpdate:
    if state.get("clarification_count", 0) >= 3:
        return translate_agent_response(
            state,
            AgentResponse(
                status="error",
                updates=PlannerUpdates(),
                error=AgentError(
                    code="REVISION_LIMIT",
                    message="The clarification limit was reached. Start a new question with more detail.",
                    source="planner",
                ),
            ),
        )
    question = state["clarification_question"]
    if not question:
        raise ValueError("No clarification question is pending")
    reply = ClarificationAnswer.model_validate(
        interrupt({"kind": "clarification", "agent": "planner", "question": question})
    )
    answer = reply.answer.strip()
    if not answer:
        raise ValueError("The clarification answer is empty")
    return ClarificationUpdate(
        user_query=f"{state['user_query']}\nClarification: {answer}",
        conversation_context=[
            *state["conversation_context"],
            ConversationMessage(role="user", content=state["user_query"]),
            ConversationMessage(role="assistant", content=question),
            ConversationMessage(role="user", content=answer),
        ],
        clarification_question=None,
        clarification_count=state.get("clarification_count", 0) + 1,
    )


def chat_graph_node(state: AgentState) -> AgentStateUpdate:
    interpretation, critique = state["interpretation"], state["critique"]
    if interpretation is None or critique is None or critique.decision != "approved":
        response = AgentResponse[ChatUpdates](
            status="error",
            updates=ChatUpdates(),
            error=AgentError(
                code="INVALID_DATA",
                message="Chat requires an approved interpretation.",
                source="chat",
            ),
        )
    else:
        answer = run_chat(
            ChatInput(
                interpretation=interpretation,
                critique=critique,
                figure_ids=[
                    a.artifact_id for a in state["artifacts"] if a.type == "figure"
                ],
            )
        )
        response = AgentResponse(
            status="success", updates=ChatUpdates(final_response=answer)
        )
    return translate_agent_response(state, response)
