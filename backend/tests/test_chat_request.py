"""Chat presents the reviewed interpretation as the final answer."""

import json
from pathlib import Path

from backend.app.api.planner_server import PlannerApp, dispatch
from backend.app.services.chat_request import present_answer
from backend.app.tools.registry import ToolRegistry


def test_present_answer_keeps_an_approved_summary() -> None:
    payload = present_answer(
        {
            "interpretation": {
                "summary": "One complete row remains.",
                "unanswered_questions": ["What about the dropped row?"],
            },
            "critique": {"decision": "approved"},
        }
    )

    assert payload["answer"]["text"] == "One complete row remains."
    assert payload["answer"]["follow_up_suggestions"] == ["What about the dropped row?"]


def test_present_answer_mentions_a_requested_revision() -> None:
    payload = present_answer(
        {
            "interpretation": {"summary": "One complete row remains."},
            "critique": {"decision": "revise"},
        }
    )

    assert "asked for a revision" in payload["answer"]["text"]


def test_present_answer_rejects_a_missing_interpretation() -> None:
    try:
        present_answer({"critique": {"decision": "approved"}})
    except ValueError as exc:
        assert str(exc) == "The interpretation is not valid"
    else:
        raise AssertionError("expected a missing interpretation to be rejected")


def test_chat_route_returns_the_final_answer() -> None:
    app = PlannerApp(Path("/tmp/ada-uploads"), ToolRegistry(), lambda: None)
    status, payload = dispatch(
        app,
        "/api/chat",
        json.dumps(
            {"interpretation": {"summary": "One complete row remains."}}
        ).encode(),
        {},
    )

    assert status == 200
    assert payload["answer"]["text"].startswith("One complete row remains.")
