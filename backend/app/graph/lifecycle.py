"""Explicit start and terminal status for a workflow run."""

from typing import TypedDict

from backend.app.contracts.errors import AgentError
from backend.app.contracts.models import RunControl
from backend.app.contracts.state import AgentState


class RunControlUpdate(TypedDict, total=False):
    control: RunControl
    errors: list[AgentError]
    last_node_error: AgentError | None


def start_run(state: AgentState) -> RunControlUpdate:
    return {
        "control": state["control"].model_copy(
            update={"status": "running", "current_agent": None}
        )
    }


def finish_run(state: AgentState) -> RunControlUpdate:
    updates: RunControlUpdate = {}
    if state["last_node_error"] is not None or state["last_node_status"] == "error":
        status = "error"
    elif state["clarification_question"] is not None:
        status = "needs_clarification"
    else:
        reason = _incomplete_reason(state)
        status = "completed" if reason is None else "error"
        if reason is not None:
            updates["errors"] = [
                *state["errors"],
                AgentError(
                    code="INVALID_DATA",
                    message=reason,
                    source="harness",
                    retryable=False,
                ),
            ]
            updates["last_node_error"] = updates["errors"][-1]
    updates["control"] = state["control"].model_copy(
        update={"status": status, "current_agent": None}
    )
    return updates


def _incomplete_reason(state: AgentState) -> str | None:
    if state["plan"] is None:
        return "Workflow ended without a validated plan."
    if state["processed_dataset"] is None or state["preprocessing_report"] is None:
        return "Workflow ended without the required preprocessing output."
    report = state["analysis_execution_report"]
    if report is None:
        return "Workflow ended without an analysis execution report."
    if report.outcome == "failed":
        return f"Analysis outcome '{report.outcome}' cannot complete this workflow."
    if not state["analysis_results"]:
        return "Workflow ended without analysis results."
    if state["interpretation"] is None:
        return "Workflow ended without an interpretation."
    critique = state["critique"]
    if (
        critique is None
        or critique.decision != "approved"
        or state["control"].current_agent != "critic"
    ):
        return "Workflow ended without Critic approval of the final interpretation."
    return None
