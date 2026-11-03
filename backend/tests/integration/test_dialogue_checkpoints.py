"""Follow-up dialogue survives checkpoint serialization as typed contracts."""

import logging

from backend.app.contracts.dialogue import DialogueTurn
from backend.app.contracts.state import create_initial_state
from backend.app.storage.workflow_checkpoints import WorkflowCheckpoints


def test_dialogue_turns_round_trip_without_blocked_types(
    tmp_path, pipeline_dataset, caplog
):
    state = create_initial_state("Compare age", pipeline_dataset)
    state.update(
        analysis_round=2,
        dialogue=[
            DialogueTurn(role="user", content="Why drop rows?", analysis_round=1),
            DialogueTurn(
                role="assistant",
                content="Rows with missing age were removed.",
                analysis_round=1,
                referenced_ids=["drop-missing"],
            ),
        ],
    )
    store = WorkflowCheckpoints(tmp_path)
    with store.open() as saver:
        encoded = saver.serde.dumps_typed(state)
    with caplog.at_level(logging.WARNING), store.open() as saver:
        restored = saver.serde.loads_typed(encoded)

    assert restored == state
    assert all(isinstance(turn, DialogueTurn) for turn in restored["dialogue"])
    assert not caplog.records
