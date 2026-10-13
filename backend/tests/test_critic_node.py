"""Basic tests for the Critic node."""

from backend.app.agents.critic.node import critic_node
from backend.app.contracts.models import (
    Critique,
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

    updates = critic_node(state, fake_model)

    assert updates["critique"].decision == "approved"


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

    updates = critic_node(state, fake_model)

    assert updates["errors"][0].code == "INVALID_DATA"
