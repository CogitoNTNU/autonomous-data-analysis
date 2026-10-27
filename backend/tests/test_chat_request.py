"""Chat presents the reviewed interpretation as the final answer."""

import json
from pathlib import Path

import pytest

from backend.app.api.planner_server import PlannerApp, dispatch
from backend.app.services.chat_request import present_answer
from backend.app.tools.registry import ToolRegistry

INTERPRETATION = {
    "summary": "Older penguins weigh more.",
    "findings": [{"claim": "Mass rises with age.", "result_ids": ["r1"]}],
    "limitations": ["Only 40 rows were complete."],
    "unanswered_questions": ["Which island?"],
}
ARTIFACTS = [
    {"artifact_id": "heatmap-1", "type": "figure"},
    {"artifact_id": "table-1", "type": "table"},
]


def _request(**overrides: object) -> dict[str, object]:
    request: dict[str, object] = {
        "interpretation": INTERPRETATION,
        "critique": {"decision": "approved"},
        "artifacts": ARTIFACTS,
    }
    return {**request, **overrides}


def test_present_answer_keeps_findings_and_only_figure_ids() -> None:
    payload = present_answer(_request())

    assert payload["status"] == "success"
    assert payload["answer"] == {
        "text": "Older penguins weigh more.",
        "findings": [{"claim": "Mass rises with age.", "result_ids": ["r1"]}],
        "limitations": ["Only 40 rows were complete."],
        "artifact_ids": ["heatmap-1"],
        "follow_up_suggestions": ["Which island?"],
    }


def test_present_answer_accepts_an_empty_artifact_list() -> None:
    payload = present_answer(_request(artifacts=[]))

    assert payload["answer"]["artifact_ids"] == []


def test_present_answer_mentions_a_requested_revision() -> None:
    payload = present_answer(_request(critique={"decision": "revise"}))

    assert "asked for a revision" in payload["answer"]["text"]


@pytest.mark.parametrize(
    "artifact",
    [
        {"artifact_id": "heatmap-1"},
        {"artifact_id": "heatmap-1", "type": "chart"},
        {"artifact_id": "", "type": "figure"},
        {"artifact_id": "heatmap-1", "type": "figure", "storage_ref": "x.png"},
        "heatmap-1",
    ],
)
def test_present_answer_rejects_a_malformed_artifact(artifact: object) -> None:
    with pytest.raises(ValueError, match="^The analysis artifacts are not valid$"):
        present_answer(_request(artifacts=[ARTIFACTS[0], artifact]))


@pytest.mark.parametrize("artifacts", [None, {}, "heatmap-1"])
def test_present_answer_rejects_artifacts_that_are_not_a_list(
    artifacts: object,
) -> None:
    with pytest.raises(ValueError, match="^The analysis artifacts are not valid$"):
        present_answer(_request(artifacts=artifacts))


def test_present_answer_rejects_missing_artifacts() -> None:
    request = _request()
    del request["artifacts"]

    with pytest.raises(ValueError, match="^The analysis artifacts are not valid$"):
        present_answer(request)


def test_present_answer_rejects_a_missing_interpretation() -> None:
    request = _request()
    del request["interpretation"]

    with pytest.raises(ValueError, match="^The interpretation is not valid$"):
        present_answer(request)


def _post_chat(request: dict[str, object]) -> tuple[int, dict[str, object]]:
    app = PlannerApp(Path("/tmp/ada-uploads"), ToolRegistry(), lambda: None)
    return dispatch(app, "/api/chat", json.dumps(request).encode(), {})


def test_chat_route_returns_the_final_answer() -> None:
    status, payload = _post_chat(_request())

    assert status == 200
    assert payload["answer"]["text"] == "Older penguins weigh more."
    assert payload["answer"]["artifact_ids"] == ["heatmap-1"]
    assert payload["answer"]["findings"][0]["result_ids"] == ["r1"]


def test_chat_route_rejects_missing_artifacts() -> None:
    status, payload = _post_chat({"interpretation": INTERPRETATION})

    assert status == 400
    assert payload == {"message": "The analysis artifacts are not valid"}
