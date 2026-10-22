from typing import Literal

from backend.app.contracts.state import AgentState


def route_after_planner(state: AgentState) -> Literal["preprocessing", "end"]:
    if state["errors"]:
        return "end"

    if state["clarification_question"] is not None:
        return "end"

    if state["plan"] is None:
        return "end"

    return "preprocessing"


def route_after_preprocessing(
        state: AgentState
) -> Literal["analysis", "end"]:
    if state["errors"]:
        return "end"

    if state["clarification_question"] is not None:
        return "end"

    if state["plan"] is None:
        return "end"

    if state["processed_dataset"] is None:
        return "end"

    if state["preprocessing_report"] is None:
        return "end"

    return "analysis"



def route_after_analysis(
        state: AgentState
) -> Literal["interpretation", "end"]:
    if state["errors"]:
        return "end"

    if state["clarification_question"] is not None:
        return "end"

    if state["plan"] is None:
        return "end"

    if state["processed_dataset"] is None:
        return "end"

    report = state["analysis_execution_report"]
    if report is None:
        return "end"

    if report.outcome != "complete":
        return "end"

    if not state["analysis_results"]:
        return "end"

    return "interpretation"
