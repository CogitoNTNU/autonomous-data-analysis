"""Lifecycle updates are explicit and do not mutate input state."""

from copy import deepcopy

import pytest

from backend.app.contracts.errors import AgentError
from backend.app.contracts.models import AnalysisExecutionReport, DatasetReference
from backend.app.contracts.state import create_initial_state
from backend.app.graph.lifecycle import finish_run, start_run


@pytest.fixture
def state():
    return create_initial_state(
        "Describe age.",
        DatasetReference(dataset_id="ages", version="v1", storage_ref="unused.csv", schema={}),
        max_revisions=4,
    )


def test_start_preserves_limits_without_mutating_state(state):
    updates = start_run(state)
    assert updates["control"].status == "running"
    assert updates["control"].max_revisions == 4
    assert updates["control"].revision_count == 0
    assert state["control"].status == "pending"


def test_finish_records_missing_output(state):
    original = deepcopy(state)
    updates = finish_run(state)
    assert updates["control"].status == "error"
    assert updates["errors"][0].source == "harness"
    assert updates["errors"][0].retryable is False
    assert updates["control"].max_revisions == 4
    assert state == original


def test_finish_preserves_existing_error(state):
    error = AgentError(code="INVALID_DATA", message="Failed.", source="preprocessing")
    state["errors"] = [error]
    state["clarification_question"] = "Old question?"
    updates = finish_run(state)
    assert updates["control"].status == "error"
    assert "errors" not in updates
    assert state["errors"] == [error]


def test_finish_marks_clarification(state):
    state["clarification_question"] = "Which column?"
    updates = finish_run(state)
    assert updates["control"].status == "needs_clarification"
    assert "errors" not in updates


@pytest.mark.parametrize("outcome", ["partial", "failed"])
def test_finish_rejects_incomplete_analysis(state, outcome):
    from backend.app.contracts.models import Plan, PreprocessingReport

    state["plan"] = Plan(plan_id="p1", objective="Describe age.")
    state["processed_dataset"] = state["dataset"]
    state["preprocessing_report"] = PreprocessingReport(rows_before=3, rows_after=3)
    state["analysis_execution_report"] = AnalysisExecutionReport(
        outcome=outcome,
        completed_step_ids=["s1"] if outcome == "partial" else [],
        failed_step_ids=["s2"],
    )
    updates = finish_run(state)
    assert updates["control"].status == "error"
    assert outcome in updates["errors"][0].message
