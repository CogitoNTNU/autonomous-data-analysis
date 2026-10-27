"""Tests for the Critic node."""

from backend.app.agents.critic.node import critic_node
from backend.app.contracts.models import (
    Critique,
    CritiqueIssue,
    DatasetReference,
    Interpretation,
)
from backend.app.contracts.state import create_initial_state


def test_critic_approves_interpretation():
    dataset = DatasetReference(
        dataset_id="test",
        version="v1",
        storage_ref="test.csv",
        dataset_schema={},
    )

    state = create_initial_state(
        user_query="Summarize the analysis",
        dataset=dataset,
    )

    state["interpretation"] = Interpretation(
        summary="The analysis has been completed.",
    )

    def fake_model(prompt, context):
        return Critique(
            decision="approved",
            issues=[],
            required_changes=[],
        )

    response = critic_node(state, fake_model)

    assert response.updates.critique.decision == "approved"


def test_critic_requires_interpretation():
    dataset = DatasetReference(
        dataset_id="test",
        version="v1",
        storage_ref="test.csv",
        dataset_schema={},
    )

    state = create_initial_state(
        user_query="Summarize the analysis",
        dataset=dataset,
    )

    def fake_model(prompt, context):
        raise AssertionError("Model should not be called")

    response = critic_node(state, fake_model)

    assert response.error.code == "INVALID_DATA"


def test_critic_handles_invalid_model_output():
    dataset = DatasetReference(
        dataset_id="test",
        version="v1",
        storage_ref="test.csv",
        dataset_schema={},
    )

    state = create_initial_state(
        user_query="Summarize the analysis",
        dataset=dataset,
    )

    state["interpretation"] = Interpretation(
        summary="The analysis has been completed.",
    )

    def fake_model(prompt, context):
        raise ValueError("Invalid LLM response")

    response = critic_node(state, fake_model)

    assert response.error.code == "INVALID_OUTPUT"
    assert response.error.source == "critic"


def test_critic_returns_revision_feedback():
    dataset = DatasetReference(
        dataset_id="test",
        version="v1",
        storage_ref="test.csv",
        dataset_schema={},
    )

    state = create_initial_state(
        user_query="Summarize the analysis",
        dataset=dataset,
    )

    state["interpretation"] = Interpretation(
        summary="The average body mass is 8000 g.",
    )

    expected_critique = Critique(
        decision="revise",
        issues=[
            CritiqueIssue(
                code="INCORRECT_VALUE",
                severity="error",
                description="The reported mean does not match the analysis.",
                target_agent="interpretation",
                related_ids=["result-1"],
            )
        ],
        required_changes=["Correct the mean using the analysis results."],
    )

    def fake_model(prompt, context):
        return expected_critique

    response = critic_node(state, fake_model)

    assert response.updates.critique == expected_critique
