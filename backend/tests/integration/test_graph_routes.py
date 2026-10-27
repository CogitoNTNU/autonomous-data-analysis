"""Test workflow routing without executing tools or reading datasets."""

from copy import deepcopy

import pytest

from backend.app.contracts.errors import AgentError
from backend.app.contracts.models import (
    AnalysisExecutionReport,
    AnalysisResult,
    DatasetReference,
    Plan,
    PreprocessingReport,
)
from backend.app.contracts.state import AgentState, create_initial_state
from backend.app.graph.routes import route_after_analysis, route_after_preprocessing


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
    ready_state,
    missing_field,
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
    ready_state["last_node_error"] = ready_state["errors"][-1]

    assert route_after_preprocessing(ready_state) == "end"


def test_route_after_preprocessing_accepts_empty_dataset(ready_state):
    ready_state["preprocessing_report"] = PreprocessingReport(
        rows_before=0,
        rows_after=0,
    )

    # Sample-size suitability belongs to Analysis, not this router.
    assert route_after_preprocessing(ready_state) == "analysis"


@pytest.fixture
def analyzed_state(ready_state) -> AgentState:
    ready_state["analysis_execution_report"] = AnalysisExecutionReport(
        outcome="complete",
        completed_step_ids=["describe-age"],
    )
    ready_state["analysis_results"] = [
        AnalysisResult(
            result_id="result-1",
            step_id="describe-age",
            dataset_version="v1",
            method="descriptive_statistics",
            values={"mean": 20.0},
            sample_size=3,
        )
    ]
    return ready_state


def test_route_after_analysis_selects_interpretation(analyzed_state):
    original = deepcopy(analyzed_state)

    assert route_after_analysis(analyzed_state) == "interpretation"
    assert analyzed_state == original


def test_route_after_analysis_sends_usable_partial_results_for_review(
    analyzed_state: AgentState,
) -> None:
    analyzed_state["analysis_execution_report"] = AnalysisExecutionReport(
        outcome="partial",
        completed_step_ids=["describe-age"],
        failed_step_ids=["other-step"],
    )
    original = deepcopy(analyzed_state)

    assert route_after_analysis(analyzed_state) == "interpretation"
    assert analyzed_state == original


@pytest.mark.parametrize(
    "missing_field",
    ["plan", "processed_dataset", "analysis_execution_report"],
)
def test_route_after_analysis_stops_on_missing_input(analyzed_state, missing_field):
    analyzed_state[missing_field] = None

    assert route_after_analysis(analyzed_state) == "end"


def test_route_after_analysis_stops_on_failed_execution(analyzed_state):
    analyzed_state["analysis_execution_report"] = AnalysisExecutionReport(
        outcome="failed",
        completed_step_ids=[],
        failed_step_ids=["other-step"],
    )

    # Results alone must not bypass the execution-report policy.
    assert analyzed_state["analysis_results"]
    assert route_after_analysis(analyzed_state) == "end"


def test_route_after_analysis_stops_without_results(analyzed_state):
    analyzed_state["analysis_results"] = []

    assert route_after_analysis(analyzed_state) == "end"


def test_route_after_analysis_stops_for_clarification(analyzed_state):
    analyzed_state["clarification_question"] = "Which age group?"

    assert route_after_analysis(analyzed_state) == "end"


def test_route_after_analysis_stops_on_error(analyzed_state):
    analyzed_state["errors"] = [
        AgentError(
            code="TOOL_FAILURE",
            message="Analysis failed.",
            source="analysis",
            retryable=False,
        )
    ]
    analyzed_state["last_node_error"] = analyzed_state["errors"][-1]

    assert route_after_analysis(analyzed_state) == "end"
