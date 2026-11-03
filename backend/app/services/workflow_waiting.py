"""Reject user input for unknown, changed, or differently paused workflows."""

from typing import Literal

from langgraph.types import StateSnapshot

from backend.app.services.interrupt_kinds import interrupt_kinds

InputKind = Literal["clarification", "message"]

_EXPECTED = {"clarification": "clarification", "message": "a message"}


def require_waiting(
    snapshot: StateSnapshot, checkpoint_id: str, kind: InputKind
) -> None:
    if not snapshot.values:
        raise ValueError("Unknown workflow")
    if snapshot.config["configurable"]["checkpoint_id"] != checkpoint_id:
        raise ValueError(
            "The workflow has changed. Refresh its status before replying."
        )
    if kind not in interrupt_kinds(snapshot):
        raise ValueError(f"This workflow is not waiting for {_EXPECTED[kind]}")
