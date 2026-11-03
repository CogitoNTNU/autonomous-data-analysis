"""Dialogue turns and chat replies keep follow-up conversation explicit."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from backend.app.contracts.dialogue import ChatReply, DialogueTurn
from backend.app.contracts.models import DatasetReference
from backend.app.contracts.state import create_initial_state
from backend.app.contracts.workflow import SendMessage, WorkflowSnapshot


def test_new_analysis_reply_carries_the_request_for_the_planner():
    reply = ChatReply(
        action="new_analysis",
        text="I will compare the groups.",
        analysis_request="Compare mean age by group",
    )

    assert reply.analysis_request == "Compare mean age by group"
    assert reply.referenced_ids == []


@pytest.mark.parametrize(
    "payload",
    [
        {"action": "answer", "text": "Done", "analysis_request": "Compare"},
        {"action": "new_analysis", "text": "I will compare."},
        {"action": "answer", "text": ""},
        {"action": "explain", "text": "Done"},
    ],
)
def test_reply_rejects_inconsistent_actions(payload):
    with pytest.raises(ValidationError):
        ChatReply.model_validate(payload)


def test_turn_defaults_to_a_plain_successful_message():
    turn = DialogueTurn(role="user", content="Why drop rows?", analysis_round=1)

    assert (turn.referenced_ids, turn.starts_analysis, turn.failed) == (
        [],
        False,
        False,
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"role": "user", "content": "Why?", "analysis_round": 0},
        {"role": "system", "content": "Why?", "analysis_round": 1},
        {"role": "user", "content": "", "analysis_round": 1},
    ],
)
def test_turn_rejects_invalid_rounds_roles_and_blank_content(payload):
    with pytest.raises(ValidationError):
        DialogueTurn.model_validate(payload)


def test_new_runs_start_in_round_one_without_dialogue():
    dataset = DatasetReference(
        dataset_id="d1", version="v1", storage_ref="data.csv", schema={}
    )

    state = create_initial_state("Mean age?", dataset)

    assert state["dialogue"] == []
    assert state["analysis_round"] == 1


def test_message_request_strips_whitespace_and_rejects_blank_messages():
    run_id = uuid4()
    request = SendMessage(run_id=run_id, checkpoint_id="c1", message="  Why?  ")

    assert request.message == "Why?"
    with pytest.raises(ValidationError):
        SendMessage(run_id=run_id, checkpoint_id="c1", message="   ")


def test_snapshots_from_older_runs_default_to_no_dialogue():
    snapshot = WorkflowSnapshot(run_id="r1", checkpoint_id="c1", status="running")

    assert snapshot.dialogue == []
    assert snapshot.analysis_round == 1
    assert snapshot.accepts_messages is False
