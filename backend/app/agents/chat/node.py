"""Present the reviewed interpretation without calculating new results."""

from backend.app.contracts.final_response import FinalResponse
from backend.app.contracts.models import Critique

from .schema import ChatInput


def run_chat(chat_input: ChatInput) -> FinalResponse:
    interpretation = chat_input.interpretation
    note = _review_note(chat_input.critique)
    text = (
        interpretation.summary if note is None else f"{interpretation.summary} {note}"
    )
    return FinalResponse(
        text=text,
        findings=interpretation.findings,
        limitations=_non_blank(interpretation.limitations),
        artifact_ids=chat_input.figure_ids,
        follow_up_suggestions=_non_blank(interpretation.unanswered_questions)[:3],
    )


def _review_note(critique: Critique | None) -> str | None:
    if critique is None:
        return "The critic did not review this answer."
    if critique.decision == "approved":
        return None
    if critique.decision == "cannot_complete":
        return "The critic could not complete the review."
    return "The critic asked for a revision before treating this as final."


def _non_blank(items: list[str]) -> list[str]:
    return [item.strip() for item in items if item.strip()]
