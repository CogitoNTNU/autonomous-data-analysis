"""Test response translation without running agents, tools, or the graph."""

import pytest

from backend.app.contracts.errors import AgentError
from backend.app.contracts.models import (
    AnalysisExecutionReport,
    AnalysisResult,
    AnalysisUpdates,
    Artifact,
    ContractModel,
    DatasetReference,
    Interpretation,
    InterpretationUpdates,
    PreprocessingReport,
    PreprocessingUpdates,
    Plan,
    PlannerUpdates,
    WarningEvent,
)
from backend.app.contracts.responses import AgentResponse
from backend.app.contracts.state import create_initial_state
from backend.app.graph.responses import translate_agent_response


@pytest.fixture
def state():
    dataset = DatasetReference(
        dataset_id="ages",
        version="v1",
        storage_ref="unused.csv",
        schema={"age": {"datatype": "integer"}},
    )
    return create_initial_state("Describe age.", dataset)


def test_translate_planner_success(state):
    state["clarification_question"] = "Old question?"
    original = state.copy()
    plan = Plan(plan_id="plan-1", objective="Describe age.")
    response = AgentResponse[PlannerUpdates](
        status="success",
        updates=PlannerUpdates(plan=plan),
    )

    updates = translate_agent_response(state, response)

    assert updates["plan"] == plan
    assert updates["clarification_question"] is None
    assert updates["warnings"] == []
    assert "errors" not in updates
    assert state == original


def test_translate_clarification_clears_previous_plan(state):
    state["plan"] = Plan(plan_id="old-plan", objective="Old objective.")
    response = AgentResponse[PlannerUpdates](
        status="needs_clarification",
        updates=PlannerUpdates(),
        clarification_question="Which age group?",
    )

    updates = translate_agent_response(state, response)

    assert updates["plan"] is None
    assert updates["clarification_question"] == "Which age group?"
    assert "errors" not in updates
    assert state["plan"].plan_id == "old-plan"
    assert state["clarification_question"] is None


def test_translate_error_preserves_history_without_mutating_state(state):
    previous_error = AgentError(
        code="TIMEOUT", message="Previous failure.", source="planner",
        retryable=False,
    )
    new_error = AgentError(
        code="INVALID_OUTPUT", message="Unknown column.", source="planner",
        retryable=False,
    )
    previous_warning = WarningEvent(
        code="PREVIOUS_WARNING", message="Previous warning.", source="planner",
    )
    new_warning = WarningEvent(
        code="NEW_WARNING", message="New warning.", source="planner",
    )
    state["errors"] = [previous_error]
    state["warnings"] = [previous_warning]
    response = AgentResponse[PlannerUpdates](
        status="error",
        updates=PlannerUpdates(),
        error=new_error,
        warnings=[new_warning],
    )

    updates = translate_agent_response(state, response)

    assert updates["errors"] == [previous_error, new_error]
    assert updates["warnings"] == [previous_warning, new_warning]
    assert updates["errors"] is not state["errors"]
    assert updates["warnings"] is not state["warnings"]
    assert state["errors"] == [previous_error]
    assert state["warnings"] == [previous_warning]


def test_translate_preprocessing_success(state):
    dataset = state["dataset"].model_copy(update={"version": "v2"})
    report = PreprocessingReport(rows_before=3, rows_after=2)
    response = AgentResponse[PreprocessingUpdates](
        status="success",
        updates=PreprocessingUpdates(
            processed_dataset=dataset,
            preprocessing_report=report,
        ),
    )

    updates = translate_agent_response(state, response)

    assert updates["processed_dataset"] == dataset
    assert updates["preprocessing_report"] == report
    assert state["processed_dataset"] is None
    assert state["preprocessing_report"] is None
    assert state["dataset"].version == "v1"


def test_translate_analysis_success(state):
    report = AnalysisExecutionReport(
        outcome="complete", completed_step_ids=["describe-age"],
    )
    result = AnalysisResult(
        result_id="result-1",
        step_id="describe-age",
        dataset_version="v1",
        method="descriptive_statistics",
        values={"mean": 20.0},
        sample_size=3,
    )
    artifact = Artifact(
        artifact_id="table-1", type="table", storage_ref="artifacts/ages.csv",
    )
    response = AgentResponse[AnalysisUpdates](
        status="success",
        updates=AnalysisUpdates(
            execution_report=report,
            analysis_results=[result],
            artifacts=[artifact],
        ),
    )

    updates = translate_agent_response(state, response)

    assert updates["analysis_execution_report"] == report
    assert "execution_report" not in updates
    assert updates["analysis_results"] == [result]
    assert updates["artifacts"] == [artifact]
    assert state["analysis_execution_report"] is None
    assert state["analysis_results"] == []
    assert state["artifacts"] == []


def test_translate_interpretation_success(state):
    interpretation = Interpretation(summary="Observed age summary.")
    response = AgentResponse[InterpretationUpdates](
        status="success",
        updates=InterpretationUpdates(interpretation=interpretation),
    )

    updates = translate_agent_response(state, response)

    assert updates["interpretation"] == interpretation
    assert state["interpretation"] is None


def test_translate_rejects_unsupported_updates(state):
    class UnsupportedUpdates(ContractModel):
        pass

    response = AgentResponse[UnsupportedUpdates](
        status="success", updates=UnsupportedUpdates(),
    )

    with pytest.raises(TypeError, match="Unsupported agent updates: UnsupportedUpdates"):
        translate_agent_response(state, response)  # type: ignore[type-var]
