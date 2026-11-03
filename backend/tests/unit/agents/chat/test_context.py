"""Chat context keeps process evidence but hides raw failures and storage paths."""

import json

import pytest
from pydantic import ValidationError

from backend.app.agents.chat.context import serialize_context
from backend.app.agents.chat.schema import ChatContext
from backend.app.contracts.models import (
    AnalysisResult,
    PreprocessingReport,
    ResultReference,
    WarningEvent,
)

PRIVATE = "private traceback /srv/data/results.json"


def _result(result_id: str, values: dict | ResultReference) -> AnalysisResult:
    return AnalysisResult(
        result_id=result_id,
        step_id=f"step-{result_id}",
        dataset_version="v2",
        method="descriptive_statistics",
        values=values,
        sample_size=3,
    )


def test_process_evidence_survives_without_private_details():
    warning = WarningEvent(code="TOOL_FAILURE", message=PRIVATE, source="analysis")
    context = ChatContext(
        message="What went wrong?",
        user_query="Describe age",
        preprocessing_report=PreprocessingReport(
            changes=["Dropped rows with missing age"],
            rows_before=5,
            rows_after=3,
            warnings=[warning],
        ),
        analysis_results=[
            _result("ok", {"mean": 20.0}),
            _result(
                "failed", {"status": "failed", "code": "TIMEOUT", "error": PRIVATE}
            ),
            _result("stored", ResultReference(storage_ref="/srv/data/results.json")),
        ],
        warnings=[warning],
    )

    serialized = serialize_context(context)
    payload = json.loads(serialized)

    assert "private" not in serialized
    assert "/srv/data" not in serialized
    assert payload["preprocessing_report"]["changes"] == [
        "Dropped rows with missing age"
    ]
    assert payload["preprocessing_report"]["rows_after"] == 3
    assert [r["values"] for r in payload["analysis_results"]] == [
        {"mean": 20.0},
        {
            "status": "failed",
            "code": "TIMEOUT",
            "error": "The planned step did not complete.",
        },
        {"status": "stored_as_artifact"},
    ]
    assert payload["valid_reference_ids"] == ["failed", "ok", "stored"]
    assert context.analysis_results[1].values["error"] == PRIVATE


def test_minimal_context_serializes_empty_evidence():
    payload = json.loads(serialize_context(ChatContext(message="Hi", user_query="Q")))

    assert payload["message"] == "Hi"
    assert payload["analysis_results"] == []
    assert payload["final_answer"] is None
    assert payload["valid_reference_ids"] == []


def test_context_requires_a_message():
    with pytest.raises(ValidationError):
        ChatContext(message="", user_query="Describe age")
