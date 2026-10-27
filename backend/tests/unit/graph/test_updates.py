"""Common graph updates preserve history without mutating agent inputs."""

import pytest

from backend.app.contracts.errors import AgentError
from backend.app.contracts.models import DatasetReference, PlannerUpdates, WarningEvent
from backend.app.contracts.responses import AgentResponse
from backend.app.contracts.state import create_initial_state
from backend.app.graph.updates import outcome_updates


@pytest.fixture
def state():
    dataset = DatasetReference(
        dataset_id="d", version="v1", storage_ref="unused", schema={}
    )
    state = create_initial_state("Describe data", dataset)
    state["warnings"] = [
        WarningEvent(code="OLD", message="Earlier warning", source="planner")
    ]
    state["errors"] = [
        AgentError(
            code="TIMEOUT", message="Earlier timeout", source="planner", retryable=True
        )
    ]
    state["clarification_question"] = "Old question?"
    state["control"].revision_count = 1
    return state


def test_success_records_latest_outcome_and_keeps_history(state):
    response = AgentResponse[PlannerUpdates](
        status="success",
        updates=PlannerUpdates(),
        warnings=[WarningEvent(code="NEW", message="New warning", source="planner")],
    )
    patch = outcome_updates(state, response, agent="planner")
    assert patch["last_node_status"] == "success"
    assert patch["control"].status == "running"
    assert patch["control"].current_agent == "planner"
    assert patch["control"].revision_count == 1
    assert patch["control"].max_revisions == 2
    assert patch["clarification_question"] is None
    assert [w.code for w in patch["warnings"]] == ["OLD", "NEW"]
    assert patch["errors"] == state["errors"]
    assert "plan" not in patch


def test_error_appends_current_failure_and_clears_question(state):
    error = AgentError(code="INVALID_DATA", message="Invalid input", source="analysis")
    response = AgentResponse[PlannerUpdates](
        status="error", updates=PlannerUpdates(), error=error
    )
    patch = outcome_updates(state, response, agent="analysis")
    assert patch["last_node_status"] == "error"
    assert patch["control"].status == "error"
    assert patch["errors"] == [*state["errors"], error]
    assert patch["clarification_question"] is None


def test_clarification_preserves_question_without_adding_error(state):
    response = AgentResponse[PlannerUpdates](
        status="needs_clarification",
        updates=PlannerUpdates(),
        clarification_question="Which column?",
    )
    patch = outcome_updates(state, response, agent="planner")
    assert patch["last_node_status"] == "needs_clarification"
    assert patch["control"].status == "needs_clarification"
    assert patch["clarification_question"] == "Which column?"
    assert patch["errors"] == state["errors"]


def test_returned_objects_are_independent(state):
    response = AgentResponse[PlannerUpdates](
        status="error",
        updates=PlannerUpdates(),
        error=AgentError(code="INVALID_DATA", message="New error", source="planner"),
    )
    patch = outcome_updates(state, response, agent="planner")
    patch["warnings"][0].message = "Changed"
    patch["errors"][0].message = "Changed"
    patch["errors"][-1].message = "Changed"
    patch["control"].revision_count = 9
    assert state["warnings"][0].message == "Earlier warning"
    assert state["errors"][0].message == "Earlier timeout"
    assert response.error.message == "New error"
    assert state["control"].revision_count == 1
    assert state["clarification_question"] == "Old question?"
    assert state["last_node_status"] is None


def test_new_run_has_no_latest_outcome_and_empty_history(state):
    fresh = create_initial_state("Describe", state["dataset"])
    response = AgentResponse[PlannerUpdates](status="success", updates=PlannerUpdates())
    patch = outcome_updates(fresh, response, agent="planner")
    assert fresh["last_node_status"] is None
    assert patch["warnings"] == []
    assert patch["errors"] == []
