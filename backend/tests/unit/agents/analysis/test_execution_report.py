"""Analysis outcomes preserve successful work and explain execution gaps."""

from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from backend.app.agents.analysis.agent import run_analysis
from backend.app.contracts.models import (
    AnalysisExecutionReport,
    DatasetReference,
    PlanStep,
)
from backend.app.contracts.state import create_initial_state
from backend.app.tools.registry import ToolRegistry


@pytest.fixture
def dataset():
    return DatasetReference(
        dataset_id="d", version="v1", storage_ref="unused.csv", schema={}
    )


def step(name, depends_on=()):
    return PlanStep(step_id=name, tool_name="unknown", depends_on=list(depends_on))


@pytest.mark.parametrize(
    "steps",
    [
        [],
        [step("a", ["missing"])],
        [step("a"), step("a")],
        [step("a", ["b"]), step("b", ["a"])],
    ],
)
def test_rejects_invalid_plan_before_execution(dataset, steps, monkeypatch):
    execute = Mock()
    monkeypatch.setattr("backend.app.agents.analysis.agent.execute_step", execute)
    response = run_analysis(dataset, steps, registry=ToolRegistry()).response
    assert response.status == "error"
    assert response.error.code == "INVALID_DATA"
    assert response.error.retryable is False
    assert response.updates.execution_report.outcome == "failed"
    assert response.updates.execution_report.failed_step_ids == []
    execute.assert_not_called()


def test_all_failed_preserves_failed_result_and_skipped_dependency(dataset):
    engine = run_analysis(
        dataset, [step("a"), step("b", ["a"])], registry=ToolRegistry()
    )
    response = engine.response
    assert response.status == "error"
    assert response.error.retryable is False
    assert response.updates.execution_report == AnalysisExecutionReport(
        outcome="failed", failed_step_ids=["a"], skipped_step_ids=["b"]
    )
    assert response.updates.analysis_results[0].values["status"] == "failed"
    assert engine.missing_steps == ["b"]
    assert engine.execution_log


@pytest.mark.parametrize(
    "payload",
    [
        {"outcome": "complete"},
        {"outcome": "partial", "completed_step_ids": ["a"]},
        {"outcome": "failed", "completed_step_ids": ["a"]},
        {"outcome": "partial", "completed_step_ids": ["a"], "failed_step_ids": ["a"]},
        {"outcome": "complete", "completed_step_ids": ["a", "a"]},
    ],
)
def test_rejects_inconsistent_report(payload):
    with pytest.raises(ValidationError):
        AnalysisExecutionReport.model_validate(payload)


def test_initial_state_has_no_execution_report(dataset):
    assert (
        create_initial_state("describe", dataset)["analysis_execution_report"] is None
    )
