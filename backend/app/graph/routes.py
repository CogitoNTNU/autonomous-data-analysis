"""Pure routing guards for the outputs required by each downstream node."""

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


def route_after_preprocessing(state: AgentState) -> Literal["analysis", "end"]:
    if state["errors"]:
        return "end"
    if state["processed_dataset"] is None or state["preprocessing_report"] is None:
        return "end"
    return "analysis"


def route_after_analysis(state: AgentState) -> Literal["interpretation", "end"]:
    if state["errors"] or state["clarification_question"] is not None:
        return "end"
    report = state["analysis_execution_report"]
    if report is None or report.outcome == "failed" or not state["analysis_results"]:
        return "end"
    # Partial results retain failure diagnostics; Interpretation validates usable evidence.
    return "interpretation"


def route_after_interpretation(state: AgentState) -> Literal["critic", "end"]:
    if state["errors"] or state["clarification_question"] is not None:
        return "end"
    if state["interpretation"] is None:
        return "end"
    return "critic"


def route_after_critic(state: AgentState) -> Literal["interpretation", "end"]:
    """Only a validated, budgeted revision can return to Interpretation."""
    if state["errors"] or state["control"].status != "running":
        return "end"
    critique = state["critique"]
    if (
        critique is not None
        and critique.decision == "revise"
        and state["control"].revision_count < state["control"].max_revisions
    ):
        return "interpretation"
    return "end"
