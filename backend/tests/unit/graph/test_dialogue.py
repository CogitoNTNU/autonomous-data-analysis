"""The dialogue node answers follow-ups without invalidating a finished analysis."""

from unittest.mock import Mock

import pytest

from backend.app.contracts.dialogue import ChatReply, DialogueTurn
from backend.app.contracts.final_response import FinalResponse
from backend.app.contracts.models import AnalysisResult, DatasetReference, RunControl
from backend.app.contracts.state import AgentState, create_initial_state
from backend.app.graph.dialogue import FAILED_REPLY, dialogue_graph_node


def _completed(message: str = "Why drop rows?") -> AgentState:
    state = create_initial_state(
        "Describe age",
        DatasetReference(dataset_id="d1", version="v1", storage_ref="a.csv", schema={}),
    )
    state.update(
        analysis_results=[
            AnalysisResult(
                result_id="r1",
                step_id="describe-age",
                dataset_version="v2",
                method="descriptive_statistics",
                values={"mean": 20.0},
                sample_size=2,
            )
        ],
        final_response=FinalResponse(text="Mean age is 20."),
        control=RunControl(status="completed", revision_count=1),
        dialogue=[DialogueTurn(role="user", content=message, analysis_round=1)],
    )
    return state


def test_answer_appends_an_assistant_turn_and_changes_nothing_else():
    reply = ChatReply(action="answer", text="Missing ages.", referenced_ids=["r1"])
    model = Mock(return_value=reply)
    state = _completed()

    update = dialogue_graph_node(state, model)

    context = model.call_args.args[1]
    assert set(update) == {"dialogue"}
    assert update["dialogue"][-1] == DialogueTurn(
        role="assistant",
        content="Missing ages.",
        analysis_round=1,
        referenced_ids=["r1"],
    )
    assert context.message == "Why drop rows?"
    assert context.dialogue == []
    assert context.final_answer.text == "Mean age is 20."


def test_new_analysis_reply_starts_the_next_round_from_the_request():
    reply = ChatReply(
        action="new_analysis",
        text="I will describe score.",
        analysis_request="Describe score",
    )

    update = dialogue_graph_node(_completed("And score?"), Mock(return_value=reply))

    assert update["user_query"] == "Describe score"
    assert update["analysis_round"] == 2
    assert update["dialogue"][-1].starts_analysis is True
    assert update["analysis_results"] == [] and update["final_response"] is None
    assert update["control"].status == "running"
    assert update["control"].revision_count == 0
    assert [m.content for m in update["conversation_context"]] == [
        "Describe age",
        "Mean age is 20.",
        "And score?",
        "I will describe score.",
    ]


@pytest.mark.parametrize(
    "failure,code,retryable",
    [
        (TimeoutError("slow"), "TIMEOUT", True),
        (ConnectionError("down"), "TOOL_FAILURE", True),
        (ValueError("bad JSON"), "INVALID_OUTPUT", False),
    ],
)
def test_model_failures_are_recorded_without_failing_the_run(failure, code, retryable):
    state = _completed()

    update = dialogue_graph_node(state, Mock(side_effect=failure))

    turn = update["dialogue"][-1]
    assert (turn.content, turn.failed) == (FAILED_REPLY, True)
    assert (update["errors"][-1].code, update["errors"][-1].retryable) == (
        code,
        retryable,
    )
    assert "last_node_error" not in update


def test_reply_citing_unknown_ids_is_a_failed_turn():
    reply = ChatReply(action="answer", text="See r9.", referenced_ids=["r9"])

    update = dialogue_graph_node(_completed(), Mock(return_value=reply))

    assert update["dialogue"][-1].failed is True
    assert update["errors"][-1].code == "INVALID_OUTPUT"


def test_node_requires_a_pending_user_message():
    state = _completed()
    state["dialogue"] = []

    with pytest.raises(ValueError, match="No follow-up message"):
        dialogue_graph_node(state, Mock())
