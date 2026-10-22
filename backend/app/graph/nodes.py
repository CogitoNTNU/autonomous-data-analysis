"""Adapt typed agent responses to LangGraph replacement state updates."""

from backend.app.agents.analysis.node import analysis_node
from backend.app.agents.interpretation.node import interpretation_node
from backend.app.agents.interpretation.schema import InterpretationModel
from backend.app.agents.planner.agent import PlannerModel
from backend.app.agents.planner.node import planner_node
from backend.app.agents.preprocessing.workflow import preprocessing_node
from backend.app.contracts.errors import AgentError
from backend.app.contracts.models import PreprocessingUpdates
from backend.app.contracts.responses import AgentResponse
from backend.app.contracts.state import AgentState
from backend.app.tools.registry import ToolRegistry

from .updates import outcome_updates


def planner_step(
    state: AgentState, registry: ToolRegistry, model: PlannerModel
) -> dict[str, object]:
    """Store the new plan and invalidate outputs from an earlier plan."""
    response = planner_node(state, registry, model)
    return {
        **outcome_updates(state, response, agent="planner"),
        "plan": response.updates.plan.model_copy(deep=True)
        if response.status == "success" and response.updates.plan is not None
        else None,
        "processed_dataset": None,
        "preprocessing_report": None,
        "analysis_execution_report": None,
        "analysis_results": [],
        "artifacts": [],
        "interpretation": None,
        "critique": None,
        "final_response": None,
    }


def preprocessing_step(state: AgentState) -> dict[str, object]:
    """Store preprocessing outputs and invalidate downstream results."""
    try:
        response = preprocessing_node(state)
    except (ValueError, OSError):
        response = AgentResponse[PreprocessingUpdates](
            status="error",
            updates=PreprocessingUpdates(),
            error=AgentError(
                code="INVALID_DATA",
                message="Preprocessing input or storage operation failed.",
                source="preprocessing",
                retryable=False,
            ),
        )
    payload = response.updates.model_copy(deep=True)
    successful = response.status == "success"
    return {
        **outcome_updates(state, response, agent="preprocessing"),
        "processed_dataset": payload.processed_dataset if successful else None,
        "preprocessing_report": payload.preprocessing_report if successful else None,
        "analysis_execution_report": None,
        "analysis_results": [],
        "artifacts": [],
        "interpretation": None,
        "critique": None,
        "final_response": None,
    }


def analysis_step(state: AgentState, registry: ToolRegistry) -> dict[str, object]:
    """Preserve execution evidence, including failed and partial outcomes."""
    response = analysis_node(state, registry)
    payload = response.updates.model_copy(deep=True)
    return {
        **outcome_updates(state, response, agent="analysis"),
        "analysis_results": payload.analysis_results,
        "artifacts": payload.artifacts,
        "analysis_execution_report": payload.execution_report,
        "interpretation": None,
        "critique": None,
        "final_response": None,
    }


def interpretation_step(
    state: AgentState, model: InterpretationModel
) -> dict[str, object]:
    """Pass revision context to the agent, then clear the previous verdict."""
    response = interpretation_node(state, model)
    draft = response.updates.interpretation
    return {
        **outcome_updates(state, response, agent="interpretation"),
        "interpretation": draft.model_copy(deep=True)
        if response.status == "success" and draft is not None
        else None,
        "critique": None,
        "final_response": None,
    }


def finish_draft(state: AgentState) -> dict[str, object]:
    """Mark a draft as ready, preserve clarification, or record a stopped run."""
    control = state["control"].model_copy(deep=True)
    if state["last_node_status"] == "needs_clarification":
        control.status = "needs_clarification"
    elif state["last_node_status"] == "error":
        control.status = "error"
    elif (
        control.current_agent == "interpretation"
        and state["interpretation"] is not None
        and state["last_node_status"] == "success"
    ):
        control.status = "draft_completed"
    else:
        control.status = "error"
        return {
            "control": control,
            "last_node_status": "error",
            "final_response": None,
            "errors": [
                *state["errors"],
                AgentError(
                    code="INVALID_OUTPUT",
                    message="Workflow stopped without required node output.",
                    source="harness",
                ),
            ],
        }
    return {"control": control, "final_response": None}
