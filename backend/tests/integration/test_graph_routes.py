"""Test preprocessing routing without executing tools or reading datasets."""

from copy import deepcopy

import pytest

from backend.app.contracts.errors import AgentError
from backend.app.contracts.models import (
    DatasetReference,
    Plan,
    PreprocessingReport,
)
from backend.app.contracts.state import AgentState, create_initial_state
from backend.app.graph.routes import route_after_preprocessing


@pytest.fixture
def ready_state() -> AgentState:
    dataset = DatasetReference(
        dataset_id="ages",
        version="v1",
        storage_ref="unused.csv",
        schema={"age": {"datatype": "integer"}},
    )
    state = create_initial_state("Describe age.", dataset)
    state["plan"] = Plan(plan_id="plan-1", objective="Describe age.")
    state["processed_dataset"] = dataset
    state["preprocessing_report"] = PreprocessingReport(
        rows_before=3,
        rows_after=3,
    )
    return state


def test_route_after_preprocessing_selects_analysis(ready_state):
    original = deepcopy(ready_state)

    assert route_after_preprocessing(ready_state) == "analysis"
    assert ready_state == original


@pytest.mark.parametrize(
    "missing_field",
    ["plan", "processed_dataset", "preprocessing_report"],
)
def test_route_after_preprocessing_stops_on_missing_input(
    ready_state, missing_field,
):
    ready_state[missing_field] = None

    assert route_after_preprocessing(ready_state) == "end"


def test_route_after_preprocessing_stops_for_clarification(ready_state):
    ready_state["clarification_question"] = "Which age group?"

    assert route_after_preprocessing(ready_state) == "end"


def test_route_after_preprocessing_stops_on_error(ready_state):
    ready_state["errors"] = [
        AgentError(
            code="INVALID_DATA",
            message="Preprocessing failed.",
            source="preprocessing",
            retryable=False,
        )
    ]

    assert route_after_preprocessing(ready_state) == "end"


def test_route_after_preprocessing_accepts_empty_dataset(ready_state):
    ready_state["preprocessing_report"] = PreprocessingReport(
        rows_before=0,
        rows_after=0,
    )

    # Sample-size suitability belongs to Analysis, not this router.
    assert route_after_preprocessing(ready_state) == "analysis"
