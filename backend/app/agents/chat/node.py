"""Present the reviewed interpretation without calculating new results."""

from backend.app.contracts.models import Critique, FinalResponse, Interpretation


def run_chat(
    interpretation: Interpretation,
    critique: Critique | None,
) -> FinalResponse:
    note = _review_note(critique)
    text = (
        interpretation.summary if note is None else f"{interpretation.summary} {note}"
    )
    return FinalResponse(
        text=text,
        follow_up_suggestions=_follow_ups(interpretation),
    )


def _review_note(critique: Critique | None) -> str | None:
    if critique is None:
        return "The critic did not review this answer."
    if critique.decision == "approved":
        return None
    if critique.decision == "cannot_complete":
        return "The critic could not complete the review."
    return "The critic asked for a revision before treating this as final."


def _follow_ups(interpretation: Interpretation) -> list[str]:
    questions = [
        question.strip()
        for question in interpretation.unanswered_questions
        if question.strip()
    ]
    return questions[:3]
