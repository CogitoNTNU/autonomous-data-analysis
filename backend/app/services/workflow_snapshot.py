"""Project persisted harness state to safe browser-facing results."""

from typing import cast

from langgraph.types import StateSnapshot

from backend.app.contracts.errors import AgentError
from backend.app.contracts.models import AgentName
from backend.app.contracts.state import AgentState
from backend.app.contracts.workflow import AnalysisOutput, WorkflowSnapshot
from backend.app.services.analysis_request import (
    figures_for,
    public_artifact,
    public_result,
)
from backend.app.services.interrupt_kinds import interrupt_kinds
from backend.app.services.workflow_review import can_retry_review


def workflow_snapshot(snapshot: StateSnapshot, *, running: bool) -> WorkflowSnapshot:
    state = cast(AgentState, snapshot.values)
    if not state:
        raise ValueError("Unknown workflow")
    error = state["last_node_error"]
    question = state["clarification_question"]
    status = "running"
    active = next(
        (
            "chat" if node == "dialogue" else node
            for node in snapshot.next
            if node
            in {
                "planner",
                "preprocessing",
                "analysis",
                "interpretation",
                "critic",
                "chat",
                "dialogue",
            }
        ),
        None,
    )
    if error and state["control"].status == "error" and not running:
        status = "error"
        active = (
            error.source
            if error.source
            in {
                "planner",
                "preprocessing",
                "analysis",
                "interpretation",
                "critic",
                "chat",
            }
            else None
        )
    elif snapshot.interrupts and question and not running:
        status = "needs_clarification"
        active = "planner"
    elif state["control"].status == "completed" and not running:
        status = "completed"
    elif not running:
        status = "error"
        error = AgentError(
            code="TOOL_FAILURE",
            message="The workflow was interrupted. Submit the question again to start a new run.",
            source="harness",
        )
    analysis = None
    if state["analysis_execution_report"] is not None:
        analysis = AnalysisOutput.model_validate(
            {
                "results": [
                    public_result(result) for result in state["analysis_results"]
                ],
                "artifacts": [
                    public_artifact(artifact) for artifact in state["artifacts"]
                ],
                "figures": figures_for(state["artifacts"]),
                "warnings": [warning.message for warning in state["warnings"]],
            }
        )
    public_error = _public_error(error)
    return WorkflowSnapshot(
        run_id=state["run_id"],
        checkpoint_id=snapshot.config["configurable"]["checkpoint_id"],
        status=status,
        active_agent=cast(AgentName | None, active),
        question=question,
        plan=state["plan"],
        report=state["preprocessing_report"],
        analysis=analysis,
        interpretation=state["interpretation"],
        critique=state["critique"],
        answer=state["final_response"],
        error=public_error,
        dialogue=state.get("dialogue", []),
        analysis_round=state.get("analysis_round", 1),
        accepts_messages=not running and "message" in interrupt_kinds(snapshot),
        can_retry_review=not running and can_retry_review(state),
    )


def _public_error(error: AgentError | None) -> AgentError | None:
    """Project safe diagnostics while retaining actionable conversion context."""
    if error is None:
        return None
    # Harness messages are authored locally and contain no provider diagnostics.
    if error.source == "harness":
        return error.model_copy(update={"details": {}})
    if error.details.get("reason") == "model_connection_failed":
        return error.model_copy(
            update={
                "details": {},
                "message": (
                    "Cannot connect to the model service. If using NTNU/IDUN, "
                    "connect to NTNU VPN or the NTNU network, then try again."
                ),
            }
        )
    if error.source == "critic" and error.code == "INVALID_OUTPUT":
        return error.model_copy(
            update={
                "details": {},
                "message": (
                    "The review service returned an invalid response. Your analysis "
                    "is saved. Retry the review to finish checking the answer."
                ),
            }
        )
    if (
        error.source == "planner"
        and error.details.get("reason") == "model_output_invalid"
    ):
        return error.model_copy(
            update={
                "details": {},
                "message": "The Planner could not return a complete valid plan after correction. Your dataset is saved. Please submit the question again.",
            }
        )
    if error.code == "TIMEOUT":
        return error.model_copy(
            update={
                "details": {},
                "message": (
                    "The model service did not respond in time during "
                    f"{error.source}. Please try again."
                ),
            }
        )
    column = error.details.get("column")
    target_type = error.details.get("target_type")
    if (
        error.source == "preprocessing"
        and error.details.get("reason") == "invalid_value"
        and isinstance(column, str)
        and isinstance(target_type, str)
    ):
        return error.model_copy(
            update={
                "details": {},
                "message": (
                    f"Preprocessing could not convert values in '{column}' "
                    f"to {target_type}."
                ),
            }
        )
    # Other diagnostics can contain provider output and filesystem locations.
    return error.model_copy(
        update={
            "details": {},
            "message": f"The {error.source} stage failed ({error.code}).",
        }
    )
