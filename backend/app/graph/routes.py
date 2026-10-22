from typing import Literal

from backend.app.contracts.state import AgentState


def route_after_planner(state: AgentState) -> Literal["preprocessing", "end"]:
    if state["last_node_status"] != "success":
        return "end"

    if state["clarification_question"] is not None:
        return "end"

    if state["plan"] is None:
        return "end"

    return "preprocessing"


def route_after_preprocessing(state: AgentState) -> Literal["analysis", "end"]:
    if (
        state["last_node_status"] == "success"
        and state["processed_dataset"] is not None
        and state["preprocessing_report"] is not None
    ):
        return "analysis"
    return "end"


def route_after_analysis(state: AgentState) -> Literal["interpretation", "end"]:
    report = state["analysis_execution_report"]
    if (
        state["last_node_status"] == "success"
        and report is not None
        and report.outcome in {"complete", "partial"}
        and report.completed_step_ids
    ):
        # Interpretation validates whether completed results are supported/usable.
        return "interpretation"
    return "end"
