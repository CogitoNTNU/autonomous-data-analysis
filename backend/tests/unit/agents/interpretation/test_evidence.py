"""Evidence preparation accepts usable results and preserves execution gaps."""

import pytest

from backend.app.agents.interpretation.evidence import prepare_evidence
from backend.app.agents.interpretation.schema import InterpretationInput
from backend.app.contracts.models import (
    AnalysisResult,
    Plan,
    PlanStep,
    PreprocessingReport,
    ResultReference,
    WarningEvent,
)


@pytest.fixture
def request_data() -> InterpretationInput:
    statistics = dict(
        mean=2.0, median=2.0, std=1.0, min=1.0, max=3.0, n=3, missing_rate=0.0
    )
    step = PlanStep(
        step_id="describe",
        tool_name="descriptive_statistics",
        arguments={"columns": ["age"]},
    )
    result = AnalysisResult(
        result_id="r1",
        step_id=step.step_id,
        dataset_version="v1",
        method=step.tool_name,
        parameters=step.arguments,
        values={"status": "ok", "columns": {"age": statistics}},
        sample_size=3,
    )
    return InterpretationInput(
        run_id="run1",
        user_query="Describe age",
        dataset_version="v1",
        plan=Plan(plan_id="p1", objective="Describe age", analysis_steps=[step]),
        analysis_results=[result],
        artifacts=[],
    )


def test_prepares_values_without_changing_or_sharing_input(request_data):
    before = request_data.model_dump()

    evidence = prepare_evidence(request_data)

    assert evidence.results[0].values == request_data.analysis_results[0].values
    assert evidence.results[0].result_id == "r1"
    assert request_data.model_dump() == before
    evidence.results[0].values["columns"]["age"]["mean"] = 99.0
    assert request_data.model_dump() == before


@pytest.mark.parametrize("field", ["mean", "median", "std", "min", "max"])
@pytest.mark.parametrize("value", [float("inf"), float("-inf"), float("nan")])
def test_rejects_nonfinite_statistics(request_data, field, value):
    request_data.analysis_results[0].values["columns"]["age"][field] = value

    with pytest.raises(ValueError, match="finite number"):
        prepare_evidence(request_data)


def test_accepts_unavailable_standard_deviation_for_single_observation(request_data):
    statistics = request_data.analysis_results[0].values["columns"]["age"]
    statistics.update(mean=2.0, median=2.0, std=None, min=2.0, max=2.0, n=1)
    request_data.analysis_results[0].sample_size = 1

    evidence = prepare_evidence(request_data)

    assert evidence.results[0].values["columns"]["age"] == statistics


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("dataset_version", "v2", "Dataset version mismatch"),
        ("step_id", "unknown", "unknown analysis step"),
        ("method", "other", "Method mismatch"),
        ("parameters", {"columns": ["other"]}, "Parameter mismatch"),
    ],
)
def test_rejects_invalid_provenance(request_data, field, value, message):
    setattr(request_data.analysis_results[0], field, value)

    with pytest.raises(ValueError, match=message):
        prepare_evidence(request_data)


@pytest.mark.parametrize("duplicate", ["result_id", "step_id", "plan_step"])
def test_rejects_duplicate_identifiers(request_data, duplicate):
    if duplicate == "plan_step":
        request_data.plan.analysis_steps.append(request_data.plan.analysis_steps[0])
    else:
        result = request_data.analysis_results[0].model_copy(deep=True)
        if duplicate == "step_id":
            result.result_id = "r2"
        request_data.analysis_results.append(result)

    with pytest.raises(ValueError, match="[Dd]uplicate|Multiple results"):
        prepare_evidence(request_data)


def test_records_failed_and_missing_steps(request_data):
    request_data.analysis_results[0].values = {"status": "failed", "error": "failed"}
    request_data.plan.analysis_steps.append(
        PlanStep(
            step_id="dependent",
            tool_name="descriptive_statistics",
            arguments={"columns": ["age"]},
            depends_on=["describe"],
        )
    )

    evidence = prepare_evidence(request_data)

    assert evidence.results == []
    assert evidence.failed_step_ids == ["describe"]
    assert evidence.missing_step_ids == ["dependent"]
    assert len(evidence.required_limitations) == 2


@pytest.mark.parametrize("unavailable", ["external", "unsupported", "empty"])
def test_records_unavailable_evidence(request_data, unavailable):
    result = request_data.analysis_results[0]
    if unavailable == "external":
        result.values = ResultReference(storage_ref="unused://table")
    elif unavailable == "unsupported":
        result.method = "future_tool"
        request_data.plan.analysis_steps[0].tool_name = "future_tool"
    else:
        result.values["columns"]["age"] = dict(
            mean=None,
            median=None,
            std=None,
            min=None,
            max=None,
            n=0,
            missing_rate=1.0,
        )

    evidence = prepare_evidence(request_data)

    assert evidence.results == []
    assert evidence.unavailable_result_ids == ["r1"]
    assert evidence.required_limitations


@pytest.mark.parametrize("invalid", ["status", "error", "columns", "count", "shape"])
def test_rejects_invalid_inline_results(request_data, invalid):
    values = request_data.analysis_results[0].values
    if invalid == "status":
        values.pop("status")
    elif invalid == "error":
        values["error"] = "contradicts success"
    elif invalid == "columns":
        values["columns"]["other"] = values["columns"].pop("age")
    elif invalid == "count":
        values["columns"]["age"]["n"] = 4
    else:
        values["columns"]["age"].pop("mean")

    with pytest.raises(ValueError):
        prepare_evidence(request_data)


def test_preserves_partial_warnings_once_and_copies_them(request_data):
    warning = WarningEvent(code="LOW_SAMPLE_SIZE", message="age n=3", source="analysis")
    request_data.warnings = [warning]
    request_data.analysis_results[0].warnings = [warning]
    request_data.analysis_results[0].values["status"] = "partial"
    request_data.preprocessing_report = PreprocessingReport(
        rows_before=3,
        rows_after=3,
        warnings=[warning],
    )

    evidence = prepare_evidence(request_data)

    assert len(evidence.results) == 1
    assert evidence.warnings == [warning]
    assert evidence.required_limitations
    evidence.warnings[0].message = "changed"
    assert warning.message == "age n=3"


def test_empty_results_record_missing_step(request_data):
    request_data.analysis_results = []

    evidence = prepare_evidence(request_data)

    assert evidence.results == []
    assert evidence.missing_step_ids == ["describe"]
