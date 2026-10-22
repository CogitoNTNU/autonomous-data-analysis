"""One interpretation attempt is bounded, grounded, and provider-independent."""

import logging
from pathlib import Path
from unittest.mock import Mock

import pytest

from backend.app.core.exceptions import ModelProviderError

from backend.app.agents.interpretation.agent import run_interpretation
from backend.app.agents.interpretation.context import DEFAULT_MAX_CONTEXT_CHARACTERS
from backend.app.agents.interpretation.schema import InterpretationInput
from backend.app.contracts.models import (
    AnalysisResult,
    Finding,
    Interpretation,
    Plan,
    PlanStep,
    WarningEvent,
)


@pytest.fixture
def request_data() -> InterpretationInput:
    warning = WarningEvent(
        code="LOW_SAMPLE_SIZE", source="analysis", message="age n=3", step_id="s1"
    )
    return InterpretationInput(
        run_id="run1",
        user_query="Describe age",
        dataset_version="v1",
        artifacts=[],
        plan=Plan(
            plan_id="p1",
            objective="Summarize age",
            assumptions=["Observations are independent"],
            analysis_steps=[
                PlanStep(
                    step_id="s1",
                    tool_name="descriptive_statistics",
                    arguments={"columns": ["age"]},
                ),
            ],
        ),
        analysis_results=[
            AnalysisResult(
                result_id="r1",
                step_id="s1",
                dataset_version="v1",
                method="descriptive_statistics",
                parameters={"columns": ["age"]},
                sample_size=3,
                warnings=[warning],
                values={
                    "status": "partial",
                    "columns": {
                        "age": {
                            "mean": 2.0,
                            "median": 2.0,
                            "std": 1.0,
                            "min": 1.0,
                            "max": 3.0,
                            "n": 3,
                            "missing_rate": 0.0,
                        }
                    },
                },
            )
        ],
    )


@pytest.fixture
def draft() -> Interpretation:
    return Interpretation(
        summary="The result describes observed ages.",
        findings=[
            Finding(claim="Mean age is 2.0 across 3 observations.", result_ids=["r1"])
        ],
    )


def test_returns_validated_draft_and_preserves_qualifications(request_data, draft):
    model = Mock(return_value=draft)
    original = request_data.model_dump()

    response = run_interpretation(request_data, model)

    assert response.status == "success"
    assert response.error is None
    assert model.call_count == 1
    prompt, context = model.call_args.args
    assert "# Interpretation Agent" in prompt
    assert context.evidence.results[0].result_id == "r1"
    assert response.updates.interpretation.findings == draft.findings
    assert (
        "Assumption: Observations are independent"
        in response.updates.interpretation.limitations
    )
    assert (
        "LOW_SAMPLE_SIZE (analysis, step s1): age n=3"
        in response.updates.interpretation.limitations
    )
    assert response.warnings[0].code == "LOW_SAMPLE_SIZE"
    assert request_data.model_dump() == original
    assert draft.limitations == []


@pytest.mark.parametrize("problem", ["version", "oversized", "mutated_input"])
def test_invalid_input_prevents_model_call(request_data, problem):
    if problem == "version":
        request_data.analysis_results[0].dataset_version = "stale"
    elif problem == "oversized":
        request_data.user_query = "x" * DEFAULT_MAX_CONTEXT_CHARACTERS
    else:
        request_data.user_query = ""
    model = Mock()

    response = run_interpretation(request_data, model)

    model.assert_not_called()
    assert response.error.code == "INVALID_DATA"
    assert response.error.retryable is False
    assert response.updates.interpretation is None


@pytest.mark.parametrize("missing", ["absent", "failed", "all_null"])
def test_no_usable_evidence_prevents_model_call(request_data, missing):
    if missing == "absent":
        request_data.analysis_results = []
    elif missing == "failed":
        request_data.analysis_results[0].values = {
            "status": "failed",
            "error": "/private/secret.csv",
        }
    else:
        request_data.analysis_results[0].values["columns"]["age"] = {
            "mean": None,
            "median": None,
            "std": None,
            "min": None,
            "max": None,
            "n": 0,
            "missing_rate": 1.0,
        }
    model = Mock()

    response = run_interpretation(request_data, model)

    model.assert_not_called()
    assert response.error.code == "INSUFFICIENT_DATA"
    assert response.updates.interpretation is None
    assert "/private/" not in response.model_dump_json()


@pytest.mark.parametrize("problem", ["citation", "blank", "wrong_type", "parse_error"])
def test_invalid_model_output_returns_safe_failure(request_data, draft, problem):
    if problem == "citation":
        draft.findings[0].result_ids = ["invented"]
    elif problem == "blank":
        draft.summary = " "
    model = Mock(return_value=None if problem == "wrong_type" else draft)
    if problem == "parse_error":
        model.side_effect = ValueError("Private provider response: secret")

    response = run_interpretation(request_data, model)

    assert model.call_count == 1
    assert response.error.code == "INVALID_OUTPUT"
    assert response.error.retryable is False
    assert response.updates.interpretation is None
    assert "secret" not in response.model_dump_json()
    assert response.warnings[0].code == "LOW_SAMPLE_SIZE"


@pytest.mark.parametrize(
    "exception,code", [(TimeoutError, "TIMEOUT"), (ConnectionError, "TOOL_FAILURE")]
)
def test_transient_failure_is_retryable_without_retrying(request_data, exception, code):
    model = Mock(side_effect=exception("private provider URL"))

    response = run_interpretation(request_data, model)

    assert model.call_count == 1
    assert response.error.code == code
    assert response.error.retryable is True
    assert "private provider URL" not in response.model_dump_json()


def test_unexpected_errors_propagate_to_workflow_boundary(request_data):
    model = Mock(side_effect=RuntimeError("unexpected defect"))

    with pytest.raises(RuntimeError, match="unexpected defect"):
        run_interpretation(request_data, model)

    assert model.call_count == 1


def test_permanent_provider_failure_is_safe_and_not_retryable(request_data):
    model = Mock(side_effect=ModelProviderError("private authentication diagnostic"))

    response = run_interpretation(request_data, model)

    assert model.call_count == 1
    assert response.error.code == "TOOL_FAILURE"
    assert response.error.retryable is False
    assert response.updates.interpretation is None
    assert "private authentication diagnostic" not in response.model_dump_json()


def test_unreadable_prompt_is_nonretryable_and_does_not_call_model(
    request_data, monkeypatch
):
    monkeypatch.setattr(
        Path, "read_text", Mock(side_effect=OSError("/private/prompt.md"))
    )
    model = Mock()

    response = run_interpretation(request_data, model)

    model.assert_not_called()
    assert response.error.code == "TOOL_FAILURE"
    assert response.error.retryable is False
    assert "/private/" not in response.model_dump_json()


def test_model_cannot_change_authoritative_evidence(request_data, draft):
    def model(prompt, context):
        context.evidence.results[0].result_id = "invented"
        context.evidence.warnings.clear()
        draft.findings[0].result_ids = ["invented"]
        return draft

    response = run_interpretation(request_data, model)

    assert response.error.code == "INVALID_OUTPUT"
    assert response.warnings
    assert request_data.analysis_results[0].result_id == "r1"


def test_partial_plan_keeps_usable_results_and_records_missing_work(
    request_data, draft
):
    request_data.plan.analysis_steps.append(
        PlanStep(
            step_id="s2",
            tool_name="descriptive_statistics",
            arguments={"columns": ["age"]},
            depends_on=["s1"],
        )
    )
    model = Mock(return_value=draft)

    response = run_interpretation(request_data, model)

    assert response.status == "success"
    assert model.call_count == 1
    assert model.call_args.args[1].evidence.missing_step_ids == ["s2"]
    assert (
        "Planned analysis step 's2' returned no result."
        in response.updates.interpretation.limitations
    )


def test_logs_identifiers_and_outcomes_without_query_or_values(
    request_data, draft, caplog
):
    request_data.user_query = "private user query"

    with caplog.at_level(logging.INFO):
        run_interpretation(request_data, Mock(return_value=draft))

    assert [record.message for record in caplog.records] == [
        "interpretation.entered",
        "interpretation.exited",
    ]
    assert caplog.records[-1].run_id == "run1"
    assert caplog.records[-1].status == "success"
    assert "private user query" not in caplog.text
