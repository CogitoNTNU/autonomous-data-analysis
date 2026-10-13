"""Prepare validated analysis evidence without model calls or dataset access."""

from pydantic import JsonValue

from backend.app.contracts.models import (
    AnalysisResult,
    Plan,
    ResultReference,
    WarningEvent,
)

from .schema import (
    DescriptiveEvidence,
    InterpretationEvidence,
    InterpretationInput,
    ResultAvailability,
    ResultEvidence,
)


def prepare_evidence(
    request: InterpretationInput,
) -> InterpretationEvidence:
    """Prepare available evidence without calculating or loading data."""
    validate_result_provenance(request)

    evidence = InterpretationEvidence(
        missing_step_ids=find_missing_steps(
            request.plan,
            request.analysis_results,
        ),
        warnings=collect_warnings(request),
    )

    for step_id in evidence.missing_step_ids:
        evidence.required_limitations.append(
            f"Planned analysis step '{step_id}' returned no result."
        )

    for result in request.analysis_results:
        _add_result(evidence, result)

    return evidence


def validate_result_provenance(
    request: InterpretationInput,
) -> None:
    """Reject results inconsistent with the supplied plan or dataset."""
    steps = {step.step_id: step for step in request.plan.analysis_steps}

    if len(steps) != len(request.plan.analysis_steps):
        raise ValueError("Plan contains duplicate analysis step IDs")

    result_ids: set[str] = set()
    completed_steps: set[str] = set()

    for result in request.analysis_results:
        if result.result_id in result_ids:
            raise ValueError(f"Duplicate result ID: {result.result_id}")

        if result.step_id in completed_steps:
            raise ValueError(f"Multiple results returned for step: {result.step_id}")

        step = steps.get(result.step_id)
        if step is None:
            raise ValueError(
                f"Result references unknown analysis step: {result.step_id}"
            )

        if result.dataset_version != request.dataset_version:
            raise ValueError(f"Dataset version mismatch for result: {result.result_id}")

        if result.method != step.tool_name:
            raise ValueError(f"Method mismatch for result: {result.result_id}")

        if result.parameters != step.arguments:
            raise ValueError(f"Parameter mismatch for result: {result.result_id}")

        result_ids.add(result.result_id)
        completed_steps.add(result.step_id)


def classify_result(
    result: AnalysisResult,
) -> ResultAvailability:
    """Identify inline evidence, execution failure, or external values."""
    if isinstance(result.values, ResultReference):
        return "external"

    status = result.values.get("status")

    if status == "failed":
        return "failed"

    if status not in ("ok", "partial"):
        raise ValueError(f"Missing or invalid status for result: {result.result_id}")

    if "error" in result.values:
        raise ValueError(f"Successful result contains an error: {result.result_id}")

    return "usable" if status == "ok" else "partial"


def validate_descriptive_values(
    values: dict[str, JsonValue],
) -> DescriptiveEvidence:
    """Validate the structure of inline descriptive statistics."""
    parsed = DescriptiveEvidence.model_validate(values, strict=True)

    if not parsed.columns:
        raise ValueError("Descriptive statistics must contain at least one column")

    return parsed


def _add_result(
    evidence: InterpretationEvidence,
    result: AnalysisResult,
) -> None:
    availability = classify_result(result)

    if availability == "failed":
        evidence.failed_step_ids.append(result.step_id)
        evidence.required_limitations.append(
            f"Analysis step '{result.step_id}' failed; "
            "its output cannot support findings."
        )
        return

    if availability == "external":
        _mark_unavailable(
            evidence,
            result,
            "its values are stored externally and have not been loaded",
        )
        return

    if result.method != "descriptive_statistics":
        _mark_unavailable(
            evidence,
            result,
            f"interpretation support for '{result.method}' has not been implemented",
        )
        return

    _add_descriptive_result(evidence, result)


def _add_descriptive_result(
    evidence: InterpretationEvidence,
    result: AnalysisResult,
) -> None:
    if not isinstance(result.values, dict):
        raise ValueError("Descriptive evidence requires inline values")

    descriptive = validate_descriptive_values(result.values)
    expected_columns = result.parameters.get("columns")
    if not isinstance(expected_columns, list) or not all(
        isinstance(column, str) for column in expected_columns
    ):
        raise ValueError("Descriptive parameters must include column names")
    if set(descriptive.columns) != set(expected_columns):
        raise ValueError(f"Returned columns do not match result: {result.result_id}")
    for column, statistics in descriptive.columns.items():
        if statistics.n > result.sample_size:
            raise ValueError(
                f"Observation count exceeds sample size for column: {column}"
            )

    if all(stats.n == 0 for stats in descriptive.columns.values()):
        _mark_unavailable(
            evidence,
            result,
            "all requested columns have zero valid observations",
        )
        return

    evidence.results.append(ResultEvidence.model_validate(result.model_dump()))
    for column, statistics in descriptive.columns.items():
        if statistics.n == 0:
            evidence.required_limitations.append(
                f"Column '{column}' has no valid observations "
                f"in result '{result.result_id}'."
            )
    if descriptive.status == "partial":
        evidence.required_limitations.append(
            f"Result '{result.result_id}' is partial; "
            "its warnings must accompany any findings."
        )


def _mark_unavailable(
    evidence: InterpretationEvidence,
    result: AnalysisResult,
    reason: str,
) -> None:
    evidence.unavailable_result_ids.append(result.result_id)
    evidence.required_limitations.append(
        f"Result '{result.result_id}' cannot support findings because {reason}."
    )


def find_missing_steps(
    plan: Plan,
    results: list[AnalysisResult],
) -> list[str]:
    """Return planned analysis steps without a corresponding result."""
    returned_steps = {result.step_id for result in results}
    return [
        step.step_id
        for step in plan.analysis_steps
        if step.step_id not in returned_steps
    ]


def collect_warnings(
    request: InterpretationInput,
) -> list[WarningEvent]:
    """Collect independent warning copies, deduplicated in encounter order."""
    candidates = list(request.warnings)
    if request.preprocessing_report is not None:
        candidates.extend(request.preprocessing_report.warnings)
    for result in request.analysis_results:
        candidates.extend(result.warnings)

    warnings: list[WarningEvent] = []
    seen: set[tuple[str, str, str | None, str]] = set()
    for warning in candidates:
        key = (warning.code, warning.source, warning.step_id, warning.message)
        if key in seen:
            continue
        seen.add(key)
        warnings.append(warning.model_copy(deep=True))
    return warnings
