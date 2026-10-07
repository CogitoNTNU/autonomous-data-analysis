"""Build bounded model context from prepared evidence, without model or tool I/O."""

from backend.app.contracts.models import Critique, WarningEvent

from .schema import (
    ArtifactContext,
    InterpretationContext,
    InterpretationEvidence,
    InterpretationInput,
)

# A configurable serialization guard, not an estimate of provider token usage.
DEFAULT_MAX_CONTEXT_CHARACTERS = 64_000


def build_context(
    request: InterpretationInput,
    evidence: InterpretationEvidence,
) -> InterpretationContext:
    """Project prepared evidence and task information into an independent context.

    Pass evidence returned by prepare_evidence. Only targeted revision feedback
    includes the previous draft; artifact storage locations are never projected.
    """
    feedback = _revision_feedback(request.critique)
    context = InterpretationContext(
        user_query=request.user_query,
        objective=request.plan.objective,
        assumptions=request.plan.assumptions,
        expected_outputs=request.plan.expected_outputs,
        evidence=evidence,
        artifacts=[
            ArtifactContext(artifact_id=item.artifact_id, type=item.type)
            for item in request.artifacts
        ],
        preprocessing_report=request.preprocessing_report,
        previous_interpretation=request.previous_interpretation if feedback else None,
        revision_feedback=feedback,
    ).model_copy(deep=True)
    _sanitize_execution_warnings(context)
    return context


def serialize_context(
    context: InterpretationContext,
    *,
    max_characters: int = DEFAULT_MAX_CONTEXT_CHARACTERS,
) -> str:
    """Serialize JSON; reject oversized context instead of dropping evidence."""
    if max_characters <= 0:
        raise ValueError("Context character limit must be positive")
    content = context.model_dump_json()
    if len(content) > max_characters:
        raise ValueError("Interpretation context exceeds the character limit")
    return content


def _revision_feedback(critique: Critique | None) -> list[str]:
    if critique is None or critique.decision != "revise":
        return []
    issues = [
        issue for issue in critique.issues if issue.target_agent == "interpretation"
    ]
    if not issues:
        return []
    feedback = [issue.description for issue in issues]
    # required_changes have no target field. Include them only when all issues
    # belong to Interpretation; mixed critiques retain the targeted descriptions.
    if len(issues) == len(critique.issues):
        feedback.extend(critique.required_changes)
    return list(dict.fromkeys(feedback))


def _sanitize_execution_warnings(context: InterpretationContext) -> None:
    """Replace known exception-bearing warnings on the newly copied context."""
    context.evidence.warnings = [
        _safe_warning(warning) for warning in context.evidence.warnings
    ]
    for result in context.evidence.results:
        result.warnings = [_safe_warning(warning) for warning in result.warnings]
    if context.preprocessing_report is not None:
        context.preprocessing_report.warnings = [
            _safe_warning(warning) for warning in context.preprocessing_report.warnings
        ]


def _safe_warning(warning: WarningEvent) -> WarningEvent:
    """Preserve data-quality details; replace known raw execution diagnostics.

    This is not a general-purpose redactor for arbitrary text in other fields.
    """
    match warning.code:
        case "TOOL_FAILURE":
            message = "A tool failed; its output may be unavailable."
        case "TIMEOUT":
            message = "A tool exceeded its execution time limit."
        case "INVALID_DATA":
            message = "An input or planned operation failed validation."
        case _:
            return warning
    return warning.model_copy(update={"message": message})
