"""Pure routing guards and diagnostics for bounded Interpretation revisions."""

from typing import Literal

from backend.app.contracts.errors import AgentError
from backend.app.contracts.models import Critique, RunControl
from backend.app.contracts.state import AgentState


def route_after_planner(state: AgentState) -> Literal["preprocessing", "end"]:
    if state["errors"] or state["clarification_question"] is not None:
        return "end"
    if state["plan"] is None:
        return "end"
    return "preprocessing"


def route_after_preprocessing(state: AgentState) -> Literal["analysis", "end"]:
    if state["errors"] or state["clarification_question"] is not None:
        return "end"
    if (
        state["plan"] is None
        or state["processed_dataset"] is None
        or state["preprocessing_report"] is None
    ):
        return "end"
    return "analysis"


def route_after_analysis(state: AgentState) -> Literal["interpretation", "end"]:
    if state["errors"] or state["clarification_question"] is not None:
        return "end"
    if state["plan"] is None or state["processed_dataset"] is None:
        return "end"
    report = state["analysis_execution_report"]
    if report is None or report.outcome == "failed" or not state["analysis_results"]:
        return "end"
    # Usable partial results retain limitations and still require Critic approval.
    return "interpretation"


def route_after_interpretation(state: AgentState) -> Literal["critic", "end"]:
    if state["errors"] or state["clarification_question"] is not None:
        return "end"
    if state["interpretation"] is None:
        return "end"
    return "critic"


def route_after_critic(state: AgentState) -> Literal["interpretation", "end"]:
    """Only a validated, budgeted revision can return to Interpretation."""
    if (
        state["errors"]
        or state["clarification_question"] is not None
        or state["control"].status != "running"
    ):
        return "end"
    critique = state["critique"]
    if (
        critique is not None
        and critique.decision == "revise"
        and critique_error(critique, state["control"]) is None
    ):
        return "interpretation"
    return "end"


def critique_error(critique: Critique, control: RunControl) -> AgentError | None:
    """Validate routing policy without changing state or consuming revision budget."""
    if critique.decision == "approved":
        return None
    if critique.decision == "cannot_complete":
        return AgentError(
            code="INSUFFICIENT_DATA",
            message="Critic could not complete review with the available evidence.",
            source="critic",
            details=critique.model_dump(mode="json"),
        )
    targets = sorted(
        {issue.target_agent for issue in critique.issues} - {"interpretation"}
    )
    if targets:
        return AgentError(
            code="INVALID_OUTPUT",
            message="Critique requires changes outside Interpretation; upstream revisions are unsupported.",
            source="critic",
            details={
                "reason": "unsupported_revision_targets",
                "target_agents": targets,
            },
        )
    if not critique.issues or any(
        not issue.description.strip() for issue in critique.issues
    ):
        return AgentError(
            code="INVALID_OUTPUT",
            message="Revision requires an actionable Interpretation-targeted issue.",
            source="critic",
            details={"reason": "missing_actionable_feedback"},
        )
    if control.revision_count >= control.max_revisions:
        return AgentError(
            code="REVISION_LIMIT",
            message="The Interpretation revision limit was reached.",
            source="critic",
            details={
                "revision_count": control.revision_count,
                "max_revisions": control.max_revisions,
            },
        )
    return None
