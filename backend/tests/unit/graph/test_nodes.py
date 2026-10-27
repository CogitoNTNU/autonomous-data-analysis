"""Graph adapters map typed outcomes without mutating shared inputs."""

from unittest.mock import Mock

import pytest

from backend.app.contracts.errors import AgentError
from backend.app.contracts.models import (
    AnalysisExecutionReport,
    AnalysisUpdates,
    DatasetReference,
    Interpretation,
    InterpretationUpdates,
    Plan,
    PlannerUpdates,
    PreprocessingReport,
    PreprocessingUpdates,
)
from backend.app.contracts.responses import AgentResponse
from backend.app.contracts.state import create_initial_state
from backend.app.graph import nodes
from backend.app.graph.routes import route_after_planner
from backend.app.tools.registry import ToolRegistry


@pytest.fixture
def state():
    dataset = DatasetReference(
        dataset_id="d", version="v1", storage_ref="unused", schema={}
    )
    state = create_initial_state("describe", dataset)
    state["plan"] = Plan(plan_id="old", objective="old")
    state["processed_dataset"] = dataset
    state["interpretation"] = Interpretation(summary="Old draft")
    return state


def test_planner_replaces_plan_and_clears_downstream(state, monkeypatch):
    plan = Plan(plan_id="new", objective="new")
    response = AgentResponse[PlannerUpdates](
        status="success", updates=PlannerUpdates(plan=plan)
    )
    monkeypatch.setattr(nodes, "planner_node", Mock(return_value=response))
    patch = nodes.planner_graph_node(state, ToolRegistry(), Mock())
    assert patch["plan"] == plan
    assert patch["processed_dataset"] is None
    assert patch["interpretation"] is None
    assert state["plan"].plan_id == "old"
    assert state["interpretation"].summary == "Old draft"
    assert route_after_planner({**state, **patch}) == "preprocessing"
    patch["plan"].objective = "Changed"
    assert plan.objective == "new"


def test_planner_clarification_clears_old_plan(state, monkeypatch):
    response = AgentResponse[PlannerUpdates](
        status="needs_clarification",
        updates=PlannerUpdates(),
        clarification_question="Which column?",
    )
    monkeypatch.setattr(nodes, "planner_node", Mock(return_value=response))
    patch = nodes.planner_graph_node(state, ToolRegistry(), Mock())
    assert patch["plan"] is None
    assert patch["clarification_question"] == "Which column?"
    assert route_after_planner({**state, **patch}) == "end"


def test_preprocessing_maps_payload_and_clears_downstream(state, monkeypatch):
    report = PreprocessingReport(rows_before=2, rows_after=2)
    response = AgentResponse[PreprocessingUpdates](
        status="success",
        updates=PreprocessingUpdates(
            processed_dataset=state["dataset"], preprocessing_report=report
        ),
    )
    monkeypatch.setattr(nodes, "preprocessing_node", Mock(return_value=response))
    patch = nodes.preprocessing_graph_node(state)
    assert patch["processed_dataset"] == state["dataset"]
    assert patch["preprocessing_report"] == report
    assert patch["analysis_results"] == []
    assert patch["interpretation"] is None


@pytest.mark.parametrize("outcome", ["partial", "failed"])
def test_analysis_preserves_report_for_partial_and_failed_execution(
    state, monkeypatch, outcome
):
    report = AnalysisExecutionReport(
        outcome=outcome,
        completed_step_ids=["a"] if outcome == "partial" else [],
        failed_step_ids=["b"],
    )
    response = AgentResponse[AnalysisUpdates](
        status="success" if outcome == "partial" else "error",
        updates=AnalysisUpdates(execution_report=report),
        error=AgentError(code="TOOL_FAILURE", message="failed", source="analysis")
        if outcome == "failed"
        else None,
    )
    monkeypatch.setattr(nodes, "analysis_node", Mock(return_value=response))
    patch = nodes.analysis_graph_node(state, ToolRegistry())
    assert patch["analysis_execution_report"] == report
    assert patch["last_node_status"] == response.status
    assert patch["interpretation"] is None


def test_interpretation_failure_clears_old_draft(state, monkeypatch):
    response = AgentResponse[InterpretationUpdates](
        status="error",
        updates=InterpretationUpdates(),
        error=AgentError(
            code="INVALID_OUTPUT", message="Invalid draft", source="interpretation"
        ),
    )
    runner = Mock(return_value=response)
    monkeypatch.setattr(nodes, "interpretation_node", runner)
    patch = nodes.interpretation_graph_node(state, Mock())
    assert runner.call_args.args[0]["interpretation"].summary == "Old draft"
    assert patch["interpretation"] is None
    assert patch["last_node_status"] == "error"
    assert state["interpretation"] is not None
