"""Chat presents the reviewed interpretation without calculating anything."""

import pytest
from pydantic import ValidationError

from backend.app.agents.chat import ChatInput, run_chat
from backend.app.contracts.models import Critique, Finding, Interpretation

SUMMARY = "Older penguins weigh more."
APPROVED = Critique(decision="approved")


def _input(
    interpretation: Interpretation | None = None,
    critique: Critique | None = APPROVED,
    figure_ids: list[str] | None = None,
) -> ChatInput:
    return ChatInput(
        interpretation=interpretation or Interpretation(summary=SUMMARY),
        critique=critique,
        figure_ids=figure_ids or [],
    )


def test_chat_keeps_findings_limitations_and_figures() -> None:
    finding = Finding(claim="Mass rises with age.", result_ids=["r1", "r2"])
    interpretation = Interpretation(
        summary=SUMMARY,
        findings=[finding],
        limitations=["Only 40 rows were complete.", "  "],
    )

    answer = run_chat(_input(interpretation, figure_ids=["heatmap-1"]))

    assert answer.text == SUMMARY
    assert answer.findings == [finding]
    assert answer.findings[0].result_ids == ["r1", "r2"]
    assert answer.limitations == ["Only 40 rows were complete."]
    assert answer.artifact_ids == ["heatmap-1"]


@pytest.mark.parametrize(
    ("critique", "note"),
    [
        (Critique(decision="revise"), "asked for a revision"),
        (Critique(decision="cannot_complete"), "could not complete the review"),
        (None, "did not review this answer"),
    ],
)
def test_chat_adds_the_review_note_after_the_summary(
    critique: Critique | None, note: str
) -> None:
    answer = run_chat(_input(critique=critique))

    assert answer.text.startswith(f"{SUMMARY} ")
    assert note in answer.text


def test_chat_caps_follow_ups_at_three_and_drops_blanks() -> None:
    interpretation = Interpretation(
        summary=SUMMARY,
        unanswered_questions=[" ", " Why? ", "", "Which island?", "When?", "Who?"],
    )

    answer = run_chat(_input(interpretation))

    assert answer.follow_up_suggestions == ["Why?", "Which island?", "When?"]


def test_chat_presents_a_summary_without_findings_or_charts() -> None:
    answer = run_chat(_input())

    assert answer.text == SUMMARY
    assert answer.findings == []
    assert answer.limitations == []
    assert answer.artifact_ids == []
    assert answer.follow_up_suggestions == []


def test_chat_input_rejects_a_blank_figure_id() -> None:
    with pytest.raises(ValidationError):
        ChatInput(
            interpretation=Interpretation(summary=SUMMARY),
            critique=APPROVED,
            figure_ids=[""],
        )


def test_chat_input_requires_an_explicit_critique() -> None:
    with pytest.raises(ValidationError):
        ChatInput.model_validate(
            {"interpretation": {"summary": SUMMARY}, "figure_ids": []}
        )
