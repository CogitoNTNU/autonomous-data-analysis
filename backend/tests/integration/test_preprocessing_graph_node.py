"""Check the preprocessing wrapper independently of graph registration."""

from unittest.mock import patch

import pytest

from backend.app.contracts.models import (
    DatasetReference,
    Plan,
    PreprocessingReport,
)
from backend.app.contracts.state import create_initial_state
from backend.app.graph.nodes import preprocessing_graph_node


@pytest.fixture
def state():
    dataset = DatasetReference(
        dataset_id="ages",
        version="v1",
        storage_ref="unused.csv",
        schema={"age": {"datatype": "integer"}},
    )
    return create_initial_state("Describe age.", dataset)


def test_preprocessing_wrapper_maps_success(state):
    state["plan"] = Plan(plan_id="plan-1", objective="Describe age.")
    dataset = state["dataset"].model_copy(update={"version": "v2"})
    report = PreprocessingReport(rows_before=3, rows_after=2)

    with patch(
        "backend.app.agents.preprocessing.workflow.run_shared_preprocessing",
        return_value=(dataset, report),
    ) as execute:
        updates = preprocessing_graph_node(state)

    execute.assert_called_once_with(state["dataset"], [])
    assert updates["processed_dataset"] == dataset
    assert updates["preprocessing_report"] == report
    assert "errors" not in updates
    assert state["processed_dataset"] is None


def test_preprocessing_wrapper_maps_missing_plan_error(state):
    updates = preprocessing_graph_node(state)

    assert len(updates["errors"]) == 1
    assert updates["errors"][0].code == "INVALID_DATA"
    assert updates["errors"][0].source == "preprocessing"
    assert updates["processed_dataset"] is None
    assert state["errors"] == []


@pytest.mark.parametrize(
    ("exception", "code"),
    [
        (FileNotFoundError("sensitive path"), "INVALID_DATA"),
        (PermissionError("sensitive path"), "TOOL_FAILURE"),
        (ValueError("sensitive value"), "INVALID_DATA"),
    ],
)
def test_preprocessing_wrapper_maps_expected_failures(state, exception, code):
    state["plan"] = Plan(plan_id="plan-1", objective="Describe age.")
    state["processed_dataset"] = state["dataset"]
    state["preprocessing_report"] = PreprocessingReport(rows_before=3, rows_after=3)

    with patch(
        "backend.app.agents.preprocessing.workflow.run_shared_preprocessing",
        side_effect=exception,
    ):
        updates = preprocessing_graph_node(state)

    error = updates["errors"][0]
    assert error.code == code
    assert error.source == "preprocessing"
    assert error.retryable is False
    assert "sensitive" not in error.message
    assert updates["processed_dataset"] is None
    assert updates["preprocessing_report"] is None
    assert state["processed_dataset"] is not None
    assert state["errors"] == []


def test_preprocessing_wrapper_does_not_hide_programming_errors(state):
    state["plan"] = Plan(plan_id="plan-1", objective="Describe age.")

    with patch(
        "backend.app.agents.preprocessing.workflow.run_shared_preprocessing",
        side_effect=TypeError("Programming error"),
    ):
        with pytest.raises(TypeError, match="Programming error"):
            preprocessing_graph_node(state)
