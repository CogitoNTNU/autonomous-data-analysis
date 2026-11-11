"""Validate recovery of a failed review while preserving computed evidence."""

from backend.app.contracts.state import AgentState


def can_retry_review(state: AgentState) -> bool:
    error = state.get("last_node_error")
    return bool(
        state
        and state["control"].status == "error"
        and error is not None
        and error.source == "critic"
        and error.code in {"INVALID_OUTPUT", "TIMEOUT", "TOOL_FAILURE"}
        and state["interpretation"] is not None
        and state["plan"] is not None
        and state["analysis_execution_report"] is not None
    )
