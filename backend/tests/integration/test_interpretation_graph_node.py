"""Test Interpretation's graph wrapper with real evidence and a fake model."""

from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock

import pytest

from backend.app.contracts.models import DatasetReference, Finding, Interpretation, Plan, PlanStep
from backend.app.contracts.state import create_initial_state
from backend.app.graph.nodes import analysis_graph_node, interpretation_graph_node
from backend.app.tools.analysis.descriptive import default_registry


@pytest.fixture
def ready_state():
    path = Path(__file__).resolve().parents[1] / "fixtures" / "clean.csv"
    dataset = DatasetReference(
        dataset_id="ages",
        version="v1",
        storage_ref=str(path),
        schema={"age": {"datatype": "integer"}},
    )
    state = create_initial_state("Describe age.", dataset)
    state["processed_dataset"] = dataset.model_copy(deep=True)
    state["plan"] = Plan(
        plan_id="describe-ages",
        objective="Describe age.",
        analysis_steps=[
            PlanStep(
                step_id="describe-age",
                tool_name="descriptive_statistics",
                arguments={"columns": ["age"]},
            ),
        ],
    )
    state.update(analysis_graph_node(state, registry=default_registry()))
    return state


def test_interpretation_wrapper_maps_success_without_mutating_state(ready_state):
    result = ready_state["analysis_results"][0]
    model = Mock(return_value=Interpretation(
        summary="Observed age summary.",
        findings=[Finding(
            claim="Mean age is 20.0 across 3 observations.",
            result_ids=[result.result_id],
        )],
    ))
    original = deepcopy(ready_state)

    updates = interpretation_graph_node(ready_state, model=model)

    model.assert_called_once()
    interpretation = updates["interpretation"]
    assert interpretation is not None
    assert interpretation.findings[0].result_ids == [result.result_id]
    assert any("LOW_SAMPLE_SIZE" in text for text in interpretation.limitations)
    assert "errors" not in updates
    assert ready_state == original


@pytest.mark.parametrize("missing_field", ["plan", "processed_dataset"])
def test_interpretation_wrapper_maps_invalid_input(ready_state, missing_field):
    ready_state[missing_field] = None
    model = Mock()

    updates = interpretation_graph_node(ready_state, model=model)

    model.assert_not_called()
    assert updates["interpretation"] is None
    assert len(updates["errors"]) == 1
    assert updates["errors"][0].code == "INVALID_DATA"
    assert updates["errors"][0].source == "interpretation"
    assert ready_state["errors"] == []


def test_interpretation_wrapper_clears_stale_draft_on_invalid_output(ready_state):
    draft = Interpretation(summary="Previous draft.")
    ready_state["interpretation"] = draft
    model = Mock(return_value=Interpretation(
        summary="Unsupported finding.",
        findings=[Finding(claim="Unsupported claim.", result_ids=["unknown-result"])],
    ))

    updates = interpretation_graph_node(ready_state, model=model)

    model.assert_called_once()
    assert updates["interpretation"] is None
    assert len(updates["errors"]) == 1
    assert updates["errors"][0].code == "INVALID_OUTPUT"
    assert ready_state["interpretation"] == draft
    assert ready_state["errors"] == []
