"""Translate plan-caused preprocessing failures into bounded Planner feedback."""

from backend.app.contracts.errors import AgentError
from backend.app.contracts.models import Critique, CritiqueIssue

ISSUE_CODE = "PREPROCESSING_PLAN_INVALID"


def is_repairable_failure(error: AgentError | None) -> bool:
    return bool(
        error is not None
        and error.code == "INVALID_DATA"
        and error.source == "preprocessing"
        and error.details.get("repair_target") == "planner"
        and error.step_id is not None
    )


def repair_critique(error: AgentError | None) -> Critique | None:
    """Return actionable Planner feedback only for structured step failures."""
    if not is_repairable_failure(error):
        return None
    assert error is not None
    assert error.step_id is not None
    tool_name = str(error.details.get("tool_name", "preprocessing tool"))
    column = error.details.get("column")
    target_type = error.details.get("target_type")
    detail = ""
    if isinstance(column, str) and isinstance(target_type, str):
        detail = (
            f" Column '{column}' contains a value that cannot be converted "
            f"to {target_type}."
        )
    return Critique(
        decision="revise",
        issues=[
            CritiqueIssue(
                code=ISSUE_CODE,
                severity="error",
                description=(
                    f"Preprocessing step '{error.step_id}' ({tool_name}) could "
                    "not execute."
                    f"{detail}"
                ),
                target_agent="planner",
                related_ids=[error.step_id],
            )
        ],
        required_changes=[
            "Remove the failing preprocessing step when it is not required by "
            "the current objective. If it is required, use an explicit "
            "invalid-value policy supported by the request or ask for "
            "clarification; do not silently discard values."
        ],
    )


def is_preprocessing_repair(critique: Critique | None) -> bool:
    return bool(
        critique is not None
        and critique.decision == "revise"
        and any(issue.code == ISSUE_CODE for issue in critique.issues)
    )
