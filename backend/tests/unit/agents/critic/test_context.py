"""Critic context preserves execution evidence without leaking raw failures."""

import json

import pytest
from pydantic import ValidationError

from backend.app.agents.critic.context import serialize_context
from backend.app.agents.critic.schema import CriticContext
from backend.app.contracts.models import (
    AnalysisExecutionReport,
    AnalysisResult,
    Interpretation,
    PreprocessingReport,
    WarningEvent,
)


def test_execution_reports_and_warnings_survive_safe_serialization():
    warning = WarningEvent(
        code="TOOL_FAILURE", message="private traceback", source="analysis"
    )
    context = CriticContext(
        user_query="Describe age",
        plan=None,
        interpretation=Interpretation(summary="Partial evidence"),
        analysis_results=[
            AnalysisResult(
                result_id="failed-result",
                step_id="failed-step",
                dataset_version="v2",
                method="descriptive_statistics",
                values={
                    "status": "failed",
                    "error": "private traceback",
                    "code": "TOOL_FAILURE",
                },
                sample_size=0,
                warnings=[warning],
            )
        ],
        preprocessing_report=PreprocessingReport(
            rows_before=5, rows_after=3, warnings=[warning]
        ),
        analysis_execution_report=AnalysisExecutionReport(
            outcome="failed", failed_step_ids=["failed-step"]
        ),
        warnings=[
            warning,
            WarningEvent(
                code="LOW_SAMPLE_SIZE",
                message="Only 3 observations.",
                source="analysis",
            ),
        ],
    )

    serialized = serialize_context(context)
    payload = json.loads(serialized)

    assert "private traceback" not in serialized
    assert payload["analysis_execution_report"]["failed_step_ids"] == ["failed-step"]
    assert payload["analysis_results"][0]["result_id"] == "failed-result"
    assert payload["preprocessing_report"]["rows_after"] == 3
    assert payload["warnings"][1]["message"] == "Only 3 observations."
    assert context.analysis_results[0].values["error"] == "private traceback"
    assert warning.message == "private traceback"


def test_context_rejects_invalid_execution_report():
    with pytest.raises(ValidationError):
        CriticContext.model_validate(
            {
                "user_query": "Describe age",
                "plan": None,
                "analysis_results": [],
                "interpretation": {"summary": "Draft"},
                "analysis_execution_report": {
                    "outcome": "complete",
                    "failed_step_ids": ["failed-step"],
                },
            }
        )


def test_context_allows_omitted_reports_for_standalone_reviews():
    context = CriticContext(
        user_query="Describe age",
        plan=None,
        analysis_results=[],
        interpretation=Interpretation(summary="Draft"),
    )
    payload = json.loads(serialize_context(context))
    assert payload["preprocessing_report"] is None
    assert payload["analysis_execution_report"] is None
    assert payload["warnings"] == []
