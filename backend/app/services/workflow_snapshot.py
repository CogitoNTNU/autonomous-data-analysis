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


def workflow_snapshot(snapshot: StateSnapshot, *, running: bool) -> WorkflowSnapshot:
    state = cast(AgentState, snapshot.values)
    if not state:
        raise ValueError("Unknown workflow")
    error = state["last_node_error"]
    question = state["clarification_question"]
    status = "running"
    active = next(
        (
            node
            for node in snapshot.next
            if node
            in {
                "planner",
                "preprocessing",
                "analysis",
                "interpretation",
                "critic",
                "chat",
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
    # Diagnostic details can contain provider output and filesystem locations.
    public_error = (
        error.model_copy(
            update={
                "details": {},
                "message": f"The {error.source} stage failed ({error.code}).",
            }
        )
        if error
        else None
    )
    if error and error.code == "TIMEOUT":
        public_error = error.model_copy(
            update={
                "details": {},
                "message": f"The model service did not respond in time during {error.source}. Please try again.",
            }
        )
    if error and error.source == "harness":
        public_error = error.model_copy(update={"details": {}})
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
    )
