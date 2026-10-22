"""Check interpretation structure and citations, not the truth of model prose."""

from backend.app.contracts.models import Finding, Interpretation, WarningEvent

from .schema import InterpretationContext, ResultEvidence


def validate_interpretation(
    interpretation: Interpretation,
    context: InterpretationContext,
) -> None:
    """Reject invalid text and citations without changing the draft or context.

    The context must come from build_context with prepared evidence. Passing
    these checks is not Critic approval: numerical fidelity, causal claims,
    and undeclared assumptions in free text still require semantic review.
    Missing qualifications are added separately by preserve_required_context.
    """
    # Revalidate because Pydantic models can be mutated after construction.
    validated = Interpretation.model_validate(interpretation.model_dump())
    _validate_text(validated)
    validate_finding_references(validated.findings, context.evidence.results)
    unavailable = set(context.evidence.unavailable_result_ids)
    blocked_steps = set(context.evidence.failed_step_ids) | set(
        context.evidence.missing_step_ids
    )
    blocked_ids = unavailable | {
        result.result_id
        for result in context.evidence.results
        if result.step_id in blocked_steps
    }
    for finding in validated.findings:
        if blocked_ids.intersection(finding.result_ids):
            raise ValueError("Finding cites unavailable or failed evidence")


def validate_finding_references(
    findings: list[Finding],
    evidence: list[ResultEvidence],
) -> None:
    """Require unique, nonblank citations to available, nonfailed results."""
    result_ids = [result.result_id for result in evidence]
    if len(result_ids) != len(set(result_ids)):
        raise ValueError("Evidence contains duplicate result IDs")
    usable_ids = {
        result.result_id
        for result in evidence
        if result.values.get("status") != "failed" and "error" not in result.values
    }
    for finding in findings:
        references = finding.result_ids
        if not references or any(not reference.strip() for reference in references):
            raise ValueError("Every finding must cite a nonblank result ID")
        if len(references) != len(set(references)):
            raise ValueError("Finding contains duplicate result references")
        if not set(references).issubset(usable_ids):
            raise ValueError("Finding cites an unknown or failed result")


def preserve_required_context(
    interpretation: Interpretation,
    context: InterpretationContext,
) -> Interpretation:
    """Validate and return an independent draft retaining required qualifications.

    The current shared contract has no warnings or assumptions_used fields, so
    these are carried in limitations. Existing prose is preserved; only exact
    duplicate limitations are removed. This operation is idempotent.
    """
    validate_interpretation(interpretation, context)
    required = [
        *context.evidence.required_limitations,
        *(f"Assumption: {assumption}" for assumption in context.assumptions),
        *(_warning_limitation(warning) for warning in _context_warnings(context)),
    ]
    result = interpretation.model_copy(deep=True)
    result.limitations = list(dict.fromkeys([*result.limitations, *required]))
    _validate_text(result)
    return result


def _validate_text(interpretation: Interpretation) -> None:
    if not interpretation.summary.strip():
        raise ValueError("Interpretation summary must not be blank")
    if any(not finding.claim.strip() for finding in interpretation.findings):
        raise ValueError("Finding claims must not be blank")
    if any(not text.strip() for text in interpretation.limitations):
        raise ValueError("Interpretation limitations must not be blank")
    if any(not text.strip() for text in interpretation.unanswered_questions):
        raise ValueError("Unanswered questions must not be blank")


def _context_warnings(context: InterpretationContext) -> list[WarningEvent]:
    warnings = list(context.evidence.warnings)
    for result in context.evidence.results:
        warnings.extend(result.warnings)
    if context.preprocessing_report is not None:
        warnings.extend(context.preprocessing_report.warnings)
    return warnings


def _warning_limitation(warning: WarningEvent) -> str:
    location = warning.source
    if warning.step_id is not None:
        location = f"{location}, step {warning.step_id}"
    return f"{warning.code} ({location}): {warning.message}"
