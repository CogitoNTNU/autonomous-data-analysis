"""Validate draft citations and preserve required qualifications without an LLM."""

import pytest

from backend.app.agents.interpretation.schema import (
    InterpretationContext,
    InterpretationEvidence,
    ResultEvidence,
)
from backend.app.agents.interpretation.validation import (
    preserve_required_context,
    validate_interpretation,
)
from backend.app.contracts.models import (
    Finding,
    Interpretation,
    PreprocessingReport,
    WarningEvent,
)


@pytest.fixture
def context() -> InterpretationContext:
    return InterpretationContext(
        user_query="Describe age",
        objective="Summarize age",
        assumptions=["Observations are independent"],
        expected_outputs=["Mean age"],
        artifacts=[],
        evidence=InterpretationEvidence(
            results=[
                ResultEvidence(
                    result_id="r1",
                    step_id="s1",
                    dataset_version="v1",
                    method="descriptive_statistics",
                    parameters={"columns": ["age"]},
                    values={"status": "ok", "columns": {"age": {"mean": 2.0, "n": 3}}},
                    sample_size=3,
                )
            ]
        ),
    )


@pytest.fixture
def draft() -> Interpretation:
    return Interpretation(
        summary="The result describes the observed ages.",
        findings=[
            Finding(
                claim="Mean age is 2.0 across 3 valid observations.", result_ids=["r1"]
            )
        ],
    )


def test_valid_draft_passes_without_mutation(draft, context):
    original = draft.model_dump()
    original_context = context.model_dump()

    validate_interpretation(draft, context)

    assert draft.model_dump() == original
    assert context.model_dump() == original_context


@pytest.mark.parametrize(
    "references", [["invented"], ["s1"], ["artifact-1"], ["r1", "r1"], [" "], []]
)
def test_rejects_invalid_citations(draft, context, references):
    draft.findings[0].result_ids = references

    with pytest.raises(ValueError):
        validate_interpretation(draft, context)


@pytest.mark.parametrize(
    "location", ["summary", "claim", "limitations", "unanswered_questions"]
)
def test_rejects_blank_text(draft, context, location):
    if location == "claim":
        draft.findings[0].claim = " \n"
    elif location == "summary":
        draft.summary = " \n"
    else:
        setattr(draft, location, [" \n"])

    with pytest.raises(ValueError, match="blank"):
        validate_interpretation(draft, context)


@pytest.mark.parametrize(
    "blocked", ["failed", "missing", "unavailable", "status", "error"]
)
def test_rejects_citations_to_blocked_results(draft, context, blocked):
    if blocked == "failed":
        context.evidence.failed_step_ids = ["s1"]
    elif blocked == "missing":
        context.evidence.missing_step_ids = ["s1"]
    elif blocked == "unavailable":
        context.evidence.unavailable_result_ids = ["r1"]
    elif blocked == "status":
        context.evidence.results[0].values["status"] = "failed"
    else:
        context.evidence.results[0].values["error"] = "Tool failed"

    with pytest.raises(ValueError, match="failed"):
        validate_interpretation(draft, context)


def test_rejects_ambiguous_duplicate_evidence(draft, context):
    context.evidence.results.append(context.evidence.results[0].model_copy(deep=True))

    with pytest.raises(ValueError, match="duplicate result IDs"):
        validate_interpretation(draft, context)


def test_accepts_limitation_only_response_without_evidence(context):
    context.evidence.results = []
    draft = Interpretation(
        summary="No usable evidence is available.", limitations=["Analysis failed."]
    )

    validate_interpretation(draft, context)

    assert draft.findings == []


def test_partial_results_can_support_findings(draft, context):
    context.evidence.results[0].values["status"] = "partial"

    validate_interpretation(draft, context)

    assert draft.findings[0].result_ids == ["r1"]


def test_preserves_qualifications_from_all_sources_once(draft, context):
    warning = WarningEvent(
        code="LOW_SAMPLE_SIZE", message="age n=3", source="analysis", step_id="s1"
    )
    preprocessing_warning = WarningEvent(
        code="PREPROCESSING_WARNING",
        message="Incomplete rows removed",
        source="preprocessing",
    )
    context.evidence.warnings = [warning]
    context.evidence.results[0].warnings = [warning]
    context.preprocessing_report = PreprocessingReport(
        rows_before=4, rows_after=3, warnings=[preprocessing_warning]
    )
    context.evidence.required_limitations = ["Comparison step returned no result."]
    draft.limitations = ["Existing qualification."]
    original_draft = draft.model_dump()
    original_context = context.model_dump()

    result = preserve_required_context(draft, context)

    assert result.limitations == [
        "Existing qualification.",
        "Comparison step returned no result.",
        "Assumption: Observations are independent",
        "LOW_SAMPLE_SIZE (analysis, step s1): age n=3",
        "PREPROCESSING_WARNING (preprocessing): Incomplete rows removed",
    ]
    assert preserve_required_context(result, context) == result
    result.findings[0].result_ids.append("changed")
    assert draft.model_dump() == original_draft
    assert context.model_dump() == original_context


def test_preserves_distinct_warning_steps(draft, context):
    context.evidence.warnings = [
        WarningEvent(
            code="LOW_SAMPLE_SIZE",
            message="Small sample",
            source="analysis",
            step_id=step,
        )
        for step in ["s1", "s2"]
    ]

    result = preserve_required_context(draft, context)

    assert "LOW_SAMPLE_SIZE (analysis, step s1): Small sample" in result.limitations
    assert "LOW_SAMPLE_SIZE (analysis, step s2): Small sample" in result.limitations


def test_preservation_does_not_repair_invalid_references(draft, context):
    draft.findings[0].result_ids = ["invented"]

    with pytest.raises(ValueError):
        preserve_required_context(draft, context)
