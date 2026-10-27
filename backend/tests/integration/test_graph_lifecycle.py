"""Lifecycle updates are explicit and do not mutate input state."""

from copy import deepcopy
from typing import Literal

import pytest
from langgraph.graph.state import CompiledStateGraph

from backend.app.contracts.errors import AgentError
from backend.app.contracts.models import (
    AnalysisExecutionReport,
    AnalysisResult,
    Critique,
    DatasetReference,
    Interpretation,
    Plan,
    PreprocessingReport,
)
from backend.app.contracts.state import AgentState, create_initial_state
from backend.app.graph.lifecycle import finish_run, start_run


@pytest.fixture
def state():
    return create_initial_state(
        "Describe age.",
        DatasetReference(
            dataset_id="ages", version="v1", storage_ref="unused.csv", schema={}
        ),
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


def test_finish_rejects_failed_analysis(state: AgentState) -> None:
    state["plan"] = Plan(plan_id="p1", objective="Describe age.")
    state["processed_dataset"] = state["dataset"]
    state["preprocessing_report"] = PreprocessingReport(rows_before=3, rows_after=3)
    state["analysis_execution_report"] = AnalysisExecutionReport(
        outcome="failed",
        completed_step_ids=[],
        failed_step_ids=["s2"],
    )
    updates = finish_run(state)
    assert updates["control"].status == "error"
    assert "failed" in updates["errors"][0].message


@pytest.fixture
def reviewed_state(state: AgentState) -> AgentState:
    state["plan"] = Plan(plan_id="p1", objective="Describe age.")
    state["processed_dataset"] = state["dataset"]
    state["preprocessing_report"] = PreprocessingReport(rows_before=3, rows_after=3)
    state["analysis_execution_report"] = AnalysisExecutionReport(
        outcome="complete", completed_step_ids=["s1"]
    )
    state["analysis_results"] = [
        AnalysisResult(
            result_id="r1",
            step_id="s1",
            dataset_version="v1",
            method="descriptive_statistics",
            values={"mean": 20.0},
            sample_size=3,
        )
    ]
    state["interpretation"] = Interpretation(summary="Observed age summary.")
    state["critique"] = Critique(decision="approved")
    state["control"] = state["control"].model_copy(
        update={"status": "running", "current_agent": "critic"}
    )
    return state


@pytest.mark.parametrize("decision", [None, "approved", "revise", "cannot_complete"])
@pytest.mark.parametrize("outcome", ["complete", "partial"])
def test_finish_requires_approval_even_for_usable_partial_results(
    reviewed_state: AgentState,
    decision: Literal["approved", "revise", "cannot_complete"] | None,
    outcome: Literal["complete", "partial"],
) -> None:
    reviewed_state["critique"] = Critique(decision=decision) if decision else None
    reviewed_state["analysis_execution_report"] = AnalysisExecutionReport(
        outcome=outcome,
        completed_step_ids=["s1"],
        failed_step_ids=["s2"] if outcome == "partial" else [],
    )
    original = deepcopy(reviewed_state)

    updates = finish_run(reviewed_state)

    assert updates["control"].current_agent is None
    if decision == "approved":
        assert updates["control"].status == "completed"
        assert "errors" not in updates
    else:
        assert updates["control"].status == "error"
        assert updates["errors"][0].source == "harness"
        assert "Critic approval" in updates["errors"][0].message
    assert reviewed_state == original


@pytest.mark.parametrize("last_agent", [None, "interpretation"])
def test_finish_rejects_approval_that_does_not_follow_final_interpretation(
    reviewed_state: AgentState, last_agent: Literal["interpretation"] | None
) -> None:
    reviewed_state["control"] = reviewed_state["control"].model_copy(
        update={"current_agent": last_agent}
    )

    updates = finish_run(reviewed_state)

    assert updates["control"].status == "error"
    assert "Critic approval" in updates["errors"][0].message


def test_compiled_graph_only_completes_in_finish_run(
    pipeline_graph: CompiledStateGraph, pipeline_dataset: DatasetReference
) -> None:
    state = create_initial_state("Describe age", pipeline_dataset, max_revisions=0)

    events = list(
        pipeline_graph.stream(
            state, stream_mode="updates", config={"recursion_limit": 12}
        )
    )

    assert [node for event in events for node in event] == [
        "start_run",
        "planner",
        "preprocessing",
        "analysis",
        "interpretation",
        "critic",
        "finish_run",
    ]
    assert events[0]["start_run"]["control"].status == "running"
    assert events[-2]["critic"]["critique"].decision == "approved"
    assert events[-2]["critic"]["control"].status == "running"
    assert events[-1]["finish_run"]["control"].status == "completed"
    assert events[-1]["finish_run"]["control"].current_agent is None
