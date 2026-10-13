"""Model context preserves evidence and projects only relevant workflow data."""

import json

import pytest

from backend.app.agents.interpretation.context import build_context, serialize_context
from backend.app.agents.interpretation.schema import (
    InterpretationContext,
    InterpretationEvidence,
    InterpretationInput,
    ResultEvidence,
)
from backend.app.contracts.models import (
    Artifact,
    Critique,
    CritiqueIssue,
    Interpretation,
    Plan,
    PreprocessingReport,
    WarningEvent,
)


@pytest.fixture
def request_data() -> InterpretationInput:
    return InterpretationInput(
        run_id="run1",
        user_query="Describe age",
        plan=Plan(
            plan_id="p1",
            objective="Summarize age",
            assumptions=["Age is measured in years"],
            expected_outputs=["Mean age"],
        ),
        dataset_version="v1",
        analysis_results=[],
        artifacts=[
            Artifact(artifact_id="a1", type="table", storage_ref="/private/a.csv")
        ],
        preprocessing_report=PreprocessingReport(
            rows_before=4,
            rows_after=3,
            changes=["Removed an incomplete row"],
        ),
    )


@pytest.fixture
def evidence() -> InterpretationEvidence:
    warning = WarningEvent(code="LOW_SAMPLE_SIZE", source="analysis", message="age n=3")
    return InterpretationEvidence(
        results=[
            ResultEvidence(
                result_id="r1",
                step_id="s1",
                dataset_version="v1",
                method="descriptive_statistics",
                parameters={"columns": ["age"]},
                values={"columns": {"age": {"mean": 2.0, "n": 3}}},
                sample_size=3,
                warnings=[warning],
            )
        ],
        warnings=[warning],
        missing_step_ids=["s2"],
        required_limitations=["Step s2 returned no result"],
    )


def test_builds_context_and_serializes_without_artifact_paths(request_data, evidence):
    context = build_context(request_data, evidence)
    content = serialize_context(context)

    assert context.user_query == request_data.user_query
    assert context.objective == request_data.plan.objective
    assert context.assumptions == request_data.plan.assumptions
    assert context.expected_outputs == request_data.plan.expected_outputs
    assert context.evidence == evidence
    assert context.preprocessing_report == request_data.preprocessing_report
    assert json.loads(content)["artifacts"] == [{"artifact_id": "a1", "type": "table"}]
    assert "/private/a.csv" not in content
    assert "storage_ref" not in content
    assert InterpretationContext.model_validate_json(content) == context


def test_context_mutation_does_not_change_inputs(request_data, evidence):
    original_request = request_data.model_dump()
    original_evidence = evidence.model_dump()

    context = build_context(request_data, evidence)
    context.assumptions.append("New assumption")
    context.evidence.results[0].values["columns"]["age"]["mean"] = 99.0
    context.evidence.warnings[0].message = "changed"
    context.preprocessing_report.changes.append("changed")

    assert request_data.model_dump() == original_request
    assert evidence.model_dump() == original_evidence


@pytest.mark.parametrize("code", ["TOOL_FAILURE", "TIMEOUT", "INVALID_DATA"])
def test_removes_raw_execution_diagnostics_from_all_warning_locations(
    request_data,
    evidence,
    code,
):
    warning = WarningEvent(
        code=code,
        source="analysis",
        step_id="s1",
        message="Exception opening /private/secret.csv",
    )
    evidence.warnings.append(warning)
    evidence.results[0].warnings.append(warning)
    request_data.preprocessing_report.warnings.append(warning)

    context = build_context(request_data, evidence)
    content = serialize_context(context)

    assert "/private/secret.csv" not in content
    assert "age n=3" in content
    assert context.evidence.warnings[-1].code == code
    assert context.evidence.warnings[-1].step_id == "s1"
    assert warning.message == "Exception opening /private/secret.csv"


def test_targeted_revision_includes_draft_and_deduplicates_changes(
    request_data, evidence
):
    request_data.previous_interpretation = Interpretation(summary="Previous draft")
    request_data.critique = Critique(
        decision="revise",
        issues=[
            CritiqueIssue(
                code="UNSUPPORTED",
                severity="error",
                target_agent="interpretation",
                description="Remove the causal claim",
            )
        ],
        required_changes=["Remove the causal claim", "Mention the sample size"],
    )

    context = build_context(request_data, evidence)

    assert context.revision_feedback == [
        "Remove the causal claim",
        "Mention the sample size",
    ]
    assert context.previous_interpretation == request_data.previous_interpretation
    context.previous_interpretation.summary = "Changed draft"
    assert request_data.previous_interpretation.summary == "Previous draft"


def test_mixed_critique_excludes_untargeted_global_changes(request_data, evidence):
    request_data.critique = Critique(
        decision="revise",
        issues=[
            CritiqueIssue(
                code="CLAIM",
                severity="error",
                target_agent="interpretation",
                description="Qualify the claim",
            ),
            CritiqueIssue(
                code="METHOD",
                severity="error",
                target_agent="planner",
                description="Choose another method",
            ),
        ],
        required_changes=["Rerun the analysis"],
    )

    context = build_context(request_data, evidence)

    assert context.revision_feedback == ["Qualify the claim"]


@pytest.mark.parametrize(
    "decision,target",
    [
        ("approved", "interpretation"),
        ("cannot_complete", "interpretation"),
        ("revise", "analysis"),
    ],
)
def test_unrelated_critique_does_not_include_old_draft(
    request_data, evidence, decision, target
):
    request_data.previous_interpretation = Interpretation(summary="Old draft")
    request_data.critique = Critique(
        decision=decision,
        issues=[
            CritiqueIssue(
                code="CHECK",
                severity="warning",
                target_agent=target,
                description="Check result",
            )
        ],
    )

    context = build_context(request_data, evidence)

    assert context.revision_feedback == []
    assert context.previous_interpretation is None


def test_optional_fields_can_be_absent(request_data):
    request_data.preprocessing_report = None
    request_data.artifacts = []

    context = build_context(request_data, InterpretationEvidence())

    assert context.preprocessing_report is None
    assert context.artifacts == []
    assert context.previous_interpretation is None
    assert context.revision_feedback == []


def test_serialization_rejects_oversized_context_without_truncation(
    request_data, evidence
):
    context = build_context(request_data, evidence)
    content = serialize_context(context)

    assert serialize_context(context, max_characters=len(content)) == content
    with pytest.raises(ValueError, match="exceeds"):
        serialize_context(context, max_characters=len(content) - 1)


@pytest.mark.parametrize("limit", [0, -1])
def test_rejects_invalid_context_limit(request_data, evidence, limit):
    context = build_context(request_data, evidence)

    with pytest.raises(ValueError, match="positive"):
        serialize_context(context, max_characters=limit)
