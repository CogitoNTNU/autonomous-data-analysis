"""Route current outcomes, bounded retries, and targeted Critic revisions."""

from typing import Literal

from backend.app.contracts.errors import AgentError
from backend.app.contracts.models import Critique, RunControl
from backend.app.contracts.state import AgentState

from .limits import can_retry

RevisionTarget = Literal["planner", "preprocessing", "analysis", "interpretation"]
REVISION_ORDER: tuple[RevisionTarget, ...] = (
    "planner",
    "preprocessing",
    "analysis",
    "interpretation",
)


def revision_target(critique: Critique) -> RevisionTarget | None:
    """For mixed issues, rerun the earliest affected stage and its dependents."""
    targets = {issue.target_agent for issue in critique.issues}
    return next((target for target in REVISION_ORDER if target in targets), None)


def _blocked(state: AgentState) -> bool:
    return (
        state["last_node_error"] is not None
        or state["last_node_status"] == "error"
        or state["clarification_question"] is not None
    )


def route_after_planner(
    state: AgentState,
) -> Literal["planner", "preprocessing", "end"]:
    if can_retry(state["last_node_error"], state["control"]):
        return "planner"
    if _blocked(state):
        return "end"
    if state["plan"] is None:
        return "end"
    return "preprocessing"


def route_after_preprocessing(
    state: AgentState,
) -> Literal["preprocessing", "analysis", "end"]:
    if can_retry(state["last_node_error"], state["control"]):
        return "preprocessing"
    if _blocked(state):
        return "end"
    if (
        state["plan"] is None
        or state["processed_dataset"] is None
        or state["preprocessing_report"] is None
    ):
        return "end"
    return "analysis"


def route_after_analysis(
    state: AgentState,
) -> Literal["analysis", "interpretation", "end"]:
    if can_retry(state["last_node_error"], state["control"]):
        return "analysis"
    if _blocked(state):
        return "end"
    if state["plan"] is None or state["processed_dataset"] is None:
        return "end"
    report = state["analysis_execution_report"]
    if report is None or report.outcome == "failed" or not state["analysis_results"]:
        return "end"
    # Usable partial results retain limitations and still require Critic approval.
    return "interpretation"


def route_after_interpretation(
    state: AgentState,
) -> Literal["interpretation", "critic", "end"]:
    if can_retry(state["last_node_error"], state["control"]):
        return "interpretation"
    if _blocked(state):
        return "end"
    if state["interpretation"] is None:
        return "end"
    return "critic"


def route_after_critic(state: AgentState) -> RevisionTarget | Literal["critic", "end"]:
    """Retry this review or route actionable feedback within the revision budget."""
    if can_retry(state["last_node_error"], state["control"]):
        return "critic"
    if _blocked(state) or state["control"].status != "running":
        return "end"
    critique = state["critique"]
    if (
        critique is not None
        and critique.decision == "revise"
        and critique_error(critique, state["control"]) is None
    ):
        return revision_target(critique) or "end"
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
        {issue.target_agent for issue in critique.issues} - set(REVISION_ORDER)
    )
    if targets:
        return AgentError(
            code="INVALID_OUTPUT",
            message="Critique requests changes from an unsupported workflow stage.",
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
            message="Revision requires an actionable issue targeting a workflow stage.",
            source="critic",
            details={"reason": "missing_actionable_feedback"},
        )
    if control.revision_count >= control.max_revisions:
        return AgentError(
            code="REVISION_LIMIT",
            message="The workflow revision limit was reached.",
            source="critic",
            details={
                "revision_count": control.revision_count,
                "max_revisions": control.max_revisions,
            },
        )
    return None
