"""Pause a completed run until the user sends a follow-up message."""

from typing import TypedDict

from langgraph.types import interrupt
from pydantic import BaseModel

from backend.app.contracts.dialogue import DialogueTurn
from backend.app.contracts.state import AgentState
from backend.app.contracts.workflow import Question


class FollowUpMessage(BaseModel):
    message: Question


class MessageUpdate(TypedDict):
    dialogue: list[DialogueTurn]


def await_message(state: AgentState) -> MessageUpdate:
    reply = FollowUpMessage.model_validate(
        interrupt({"kind": "message", "agent": "chat"})
    )
    turn = DialogueTurn(
        role="user",
        content=reply.message,
        analysis_round=state.get("analysis_round", 1),
    )
    return MessageUpdate(dialogue=[*state.get("dialogue", []), turn])
