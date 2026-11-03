"""Chat replies are grounded in IDs the analysis actually produced."""

from unittest.mock import Mock

import pytest

from backend.app.agents.chat.reply import reply_to_message
from backend.app.agents.chat.schema import ChatContext, PresentedArtifact
from backend.app.contracts.dialogue import ChatReply
from backend.app.contracts.models import AnalysisResult, Plan, PlanStep


def _context() -> ChatContext:
    return ChatContext(
        message="Why did you drop rows?",
        user_query="Describe age",
        plan=Plan(
            plan_id="p1",
            objective="Describe age",
            preprocessing_steps=[PlanStep(step_id="drop-missing", tool_name="drop")],
            analysis_steps=[PlanStep(step_id="describe-age", tool_name="describe")],
        ),
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
        artifacts=[PresentedArtifact(artifact_id="figure-1", type="figure")],
    )


def test_answer_receives_the_prompt_and_a_copy_of_the_context():
    reply = ChatReply(
        action="answer", text="Missing ages were removed.", referenced_ids=["r1"]
    )
    model = Mock(return_value=reply)
    context = _context()

    result = reply_to_message(context, model)

    prompt, sent = model.call_args.args
    assert result == reply
    assert "Chat Agent" in prompt
    assert sent == context
    assert sent is not context


def test_reply_citing_an_unknown_result_is_rejected():
    model = Mock(
        return_value=ChatReply(
            action="answer", text="See r9.", referenced_ids=["r1", "r9"]
        )
    )

    with pytest.raises(ValueError, match="unknown analysis IDs"):
        reply_to_message(_context(), model)


def test_plan_step_and_artifact_ids_are_valid_references():
    reply = ChatReply(
        action="new_analysis",
        text="I will compare age by group.",
        referenced_ids=["p1", "drop-missing", "describe-age", "figure-1"],
        analysis_request="Compare mean age by group",
    )

    assert reply_to_message(_context(), Mock(return_value=reply)) == reply


def test_without_a_plan_only_result_ids_are_known():
    context = _context().model_copy(update={"plan": None})
    model = Mock(
        return_value=ChatReply(
            action="answer", text="It was dropped.", referenced_ids=["drop-missing"]
        )
    )

    with pytest.raises(ValueError):
        reply_to_message(context, model)
