"""After an analysis, users can ask about the process or request a new analysis."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from backend.app.agents.planner.schema import ClarificationRequest, PlannerOutput
from backend.app.api.planner_server import PlannerApp, dispatch
from backend.app.contracts.dialogue import ChatReply

from .workflow_helpers import send, settled, start

ANSWER = ChatReply(action="answer", text="Rows without age were removed.")


@pytest.fixture
def chat() -> Mock:
    return Mock(return_value=ANSWER)


@pytest.fixture
def dialogue_app(pipeline_dataset, pipeline_registry, pipeline_models, chat, tmp_path):
    planner, interpretation, critic = pipeline_models
    app = PlannerApp(
        tmp_path,
        pipeline_registry,
        lambda: planner,
        lambda: interpretation,
        lambda: critic,
    )
    app.workflows.chat = lambda: chat
    data = Path(pipeline_dataset.storage_ref).read_bytes()
    code, registered = dispatch(app, "/api/datasets", data, {})
    assert code == 200
    pipeline_dataset.dataset_id = registered["dataset_id"]
    yield app
    app.workflows.close()


@pytest.fixture
def completed(dialogue_app, pipeline_dataset) -> dict:
    result = settled(dialogue_app, start(dialogue_app, pipeline_dataset)["run_id"])
    assert result["status"] == "completed", result
    assert result["accepts_messages"] is True
    return result


def test_question_about_the_process_is_answered_from_the_finished_run(
    dialogue_app, completed, chat, pipeline_models
):
    question = "Why were rows removed?"
    assert send(dialogue_app, completed, question)[0] == 200
    result = settled(dialogue_app, completed["run_id"])

    context = chat.call_args.args[1]
    assert result["status"] == "completed", result
    assert [turn["content"] for turn in result["dialogue"]] == [question, ANSWER.text]
    assert result["answer"] == completed["answer"]
    assert result["analysis"] == completed["analysis"]
    assert result["accepts_messages"] is True
    assert context.message == question
    assert context.preprocessing_report.rows_before == 3
    assert pipeline_models[0].call_count == 1


def test_request_for_new_calculations_runs_a_second_analysis_round(
    dialogue_app, completed, chat, pipeline_models
):
    chat.return_value = ChatReply(
        action="new_analysis",
        text="I will describe age again.",
        analysis_request="Describe age without missing values",
    )

    assert send(dialogue_app, completed, "Can you redo it?")[0] == 200
    result = settled(dialogue_app, completed["run_id"])

    context = pipeline_models[0].call_args.args[1]
    assert (result["status"], result["analysis_round"]) == ("completed", 2)
    assert result["dialogue"][1]["starts_analysis"] is True
    assert result["answer"] is not None and result["accepts_messages"] is True
    assert pipeline_models[0].call_count == 2
    assert context.user_query == "Describe age without missing values"
    assert [m.content for m in context.conversation_context][:2] == [
        "Describe age",
        completed["answer"]["text"],
    ]


def test_failed_reply_keeps_the_analysis_and_allows_another_message(
    dialogue_app, completed, chat
):
    chat.side_effect = TimeoutError("provider details")

    assert send(dialogue_app, completed, "Why?")[0] == 200
    result = settled(dialogue_app, completed["run_id"])

    assert result["status"] == "completed" and result["error"] is None
    assert result["dialogue"][1]["failed"] and result["accepts_messages"]
    assert "provider details" not in str(result)


def test_messages_require_the_current_checkpoint_and_a_waiting_run(
    dialogue_app, completed, pipeline_dataset, pipeline_models, pipeline_plan
):
    stale = {**completed, "checkpoint_id": "stale"}
    code, payload = send(dialogue_app, stale, "Why?")
    assert code == 400 and "workflow has changed" in payload["message"]
    assert send(dialogue_app, completed, "   ")[0] == 422
    pipeline_models[0].side_effect = [
        PlannerOutput(clarification=ClarificationRequest(question="Which column?")),
        PlannerOutput(plan=pipeline_plan),
    ]
    waiting = settled(dialogue_app, start(dialogue_app, pipeline_dataset)["run_id"])
    code, payload = send(dialogue_app, waiting, "Why?")
    assert waiting["accepts_messages"] is False
    assert (code, payload["message"]) == (
        400,
        "This workflow is not waiting for a message",
    )


def test_dialogue_ends_at_the_message_limit(dialogue_app, completed, monkeypatch):
    monkeypatch.setattr(
        "backend.app.graph.conversation_wiring.MAX_DIALOGUE_MESSAGES", 1
    )

    assert send(dialogue_app, completed, "Why?")[0] == 200
    result = settled(dialogue_app, completed["run_id"])

    assert result["status"] == "completed"
    assert result["accepts_messages"] is False
    assert send(dialogue_app, result, "And?")[0] == 400


def test_dialogue_survives_a_backend_restart(
    dialogue_app, completed, pipeline_registry, tmp_path
):
    assert send(dialogue_app, completed, "Why?")[0] == 200
    settled(dialogue_app, completed["run_id"])
    restarted = PlannerApp(tmp_path, pipeline_registry, Mock(), Mock(), Mock())
    try:
        result = settled(restarted, completed["run_id"])
    finally:
        restarted.workflows.close()

    assert len(result["dialogue"]) == 2
    assert result["accepts_messages"] is True
