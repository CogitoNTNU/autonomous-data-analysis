"""A new analysis round keeps the source dataset and a bounded conversation."""

from backend.app.contracts.dialogue import MAX_DIALOGUE_MESSAGES, DialogueTurn
from backend.app.contracts.models import ConversationMessage, DatasetReference
from backend.app.contracts.state import create_initial_state
from backend.app.graph.new_analysis import new_analysis_update

DATASET = DatasetReference(
    dataset_id="d1", version="v1", storage_ref="a.csv", schema={}
)


def test_only_the_current_round_dialogue_is_added_to_the_context():
    state = create_initial_state("Describe score", DATASET)
    state["analysis_round"] = 2
    dialogue = [
        DialogueTurn(role="user", content="Old question", analysis_round=1),
        DialogueTurn(role="user", content="New question", analysis_round=2),
    ]

    update = new_analysis_update(state, "Compare groups", dialogue)

    assert [m.content for m in update["conversation_context"]] == [
        "Describe score",
        "New question",
    ]
    assert update["analysis_round"] == 3
    assert update["dialogue"] == dialogue


def test_conversation_context_is_capped_to_the_most_recent_messages():
    earlier = [
        ConversationMessage(role="user", content=f"message {index}")
        for index in range(MAX_DIALOGUE_MESSAGES + 5)
    ]
    state = create_initial_state("Describe age", DATASET, conversation_context=earlier)

    update = new_analysis_update(state, "Compare groups", [])

    assert len(update["conversation_context"]) == MAX_DIALOGUE_MESSAGES
    assert update["conversation_context"][-1].content == "Describe age"


def test_new_round_keeps_the_source_dataset_and_clears_clarifications():
    state = create_initial_state("Describe age", DATASET)
    state.update(clarification_question="Which column?", clarification_count=2)

    update = new_analysis_update(state, "Compare groups", [])

    assert "dataset" not in update
    assert update["processed_dataset"] is None
    assert update["clarification_question"] is None
    assert update["clarification_count"] == 0
