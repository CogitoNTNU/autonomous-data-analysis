"""The compiled graph passes validated results through one Critic review."""

from pathlib import Path
from unittest.mock import Mock

import pytest
from langgraph.graph.state import CompiledStateGraph

from backend.app.contracts.models import (
    Critique,
    DatasetReference,
    Interpretation,
    Plan,
    PlanStep,
    WarningEvent,
)
from backend.app.contracts.state import create_initial_state


def test_full_pipeline_runs_once_and_preserves_typed_outputs(
    pipeline_graph: CompiledStateGraph,
    pipeline_dataset: DatasetReference,
    pipeline_models: tuple[Mock, Mock, Mock],
) -> None:
    planner, interpretation, critic = pipeline_models
    original = Path(pipeline_dataset.storage_ref).read_bytes()
    state = create_initial_state("Describe age", pipeline_dataset, max_revisions=0)
    warning = WarningEvent(
        code="DATA_NOTE", message="Recorded ages", source="ingestion"
    )
    state["warnings"] = [warning]

    result = pipeline_graph.invoke(state, config={"recursion_limit": 10})

    planner.assert_called_once()
    interpretation.assert_called_once()
    critic.assert_called_once()
    assert result["plan"] == planner.return_value.plan
    assert result["dataset"] == pipeline_dataset
    processed = result["processed_dataset"]
    assert isinstance(processed, DatasetReference)
    assert processed.version != pipeline_dataset.version
    assert result["preprocessing_report"].rows_before == 3
    assert result["preprocessing_report"].rows_after == 2
    assert result["analysis_execution_report"].outcome == "complete"
    analysis = result["analysis_results"][0]
    assert analysis.dataset_version == processed.version
    assert analysis.values["columns"]["age"]["mean"] == 20.0
    assert analysis.sample_size == 2
    assert result["interpretation"].findings[0].result_ids == [analysis.result_id]
    assert critic.call_args.args[1].interpretation == result["interpretation"]
    assert critic.call_args.args[1].analysis_results == result["analysis_results"]
    assert result["critique"].decision == "approved"
    assert result["control"].status == "completed"
    assert result["errors"] == []
    assert result["warnings"][0] == warning
    assert len(result["warnings"]) == len(analysis.warnings) + 1
    assert any(
        "LOW_SAMPLE_SIZE" in text for text in result["interpretation"].limitations
    )
    assert result["control"].revision_count == 0
    assert result["final_response"] is None
    assert state["analysis_results"] == []
    assert state["interpretation"] is None
    assert state["warnings"] == [warning]
    assert Path(pipeline_dataset.storage_ref).read_bytes() == original


def test_pipeline_accepts_no_op_preprocessing(
    pipeline_graph: CompiledStateGraph,
    pipeline_dataset: DatasetReference,
    pipeline_plan: Plan,
    pipeline_models: tuple[Mock, Mock, Mock],
) -> None:
    pipeline_plan.preprocessing_steps = []
    pipeline_plan.analysis_steps[0].depends_on = []
    state = create_initial_state("Describe age", pipeline_dataset, max_revisions=0)

    result = pipeline_graph.invoke(state, config={"recursion_limit": 10})

    assert result["processed_dataset"].version == pipeline_dataset.version
    assert result["preprocessing_report"].changes == []
    assert result["critique"].decision == "approved"
    pipeline_models[2].assert_called_once()


@pytest.mark.parametrize(
    "failure", [ValueError("private details"), OSError("private path")]
)
def test_preprocessing_failure_stops_downstream_nodes(
    pipeline_graph: CompiledStateGraph,
    pipeline_dataset: DatasetReference,
    pipeline_models: tuple[Mock, Mock, Mock],
    monkeypatch: pytest.MonkeyPatch,
    failure: Exception,
) -> None:
    monkeypatch.setattr(
        "backend.app.graph.nodes.preprocessing_node", Mock(side_effect=failure)
    )
    state = create_initial_state("Describe age", pipeline_dataset, max_revisions=0)

    result = pipeline_graph.invoke(state, config={"recursion_limit": 10})

    assert result["errors"][0].source == "preprocessing"
    assert "private" not in result["errors"][0].message
    assert result["processed_dataset"] is None
    assert result["analysis_execution_report"] is None
    pipeline_models[1].assert_not_called()
    pipeline_models[2].assert_not_called()


@pytest.mark.parametrize("partial", [True, False])
def test_analysis_gaps_continue_only_with_successful_evidence(
    pipeline_graph: CompiledStateGraph,
    pipeline_dataset: DatasetReference,
    pipeline_plan: Plan,
    pipeline_models: tuple[Mock, Mock, Mock],
    partial: bool,
) -> None:
    if not partial:
        pipeline_plan.analysis_steps = []
    pipeline_plan.analysis_steps.extend(
        [
            PlanStep(
                step_id="failed",
                tool_name="failing_statistics",
                arguments={"columns": ["age"]},
            ),
            PlanStep(
                step_id="blocked",
                tool_name="descriptive_statistics",
                arguments={"columns": ["score"]},
                depends_on=["failed"],
            ),
        ]
    )
    state = create_initial_state("Describe age", pipeline_dataset, max_revisions=0)

    result = pipeline_graph.invoke(state, config={"recursion_limit": 10})

    report = result["analysis_execution_report"]
    assert report.outcome == ("partial" if partial else "failed")
    assert report.failed_step_ids == ["failed"]
    assert report.skipped_step_ids == ["blocked"]
    assert any(warning.code == "DEPENDENCY_FAILED" for warning in result["warnings"])
    if partial:
        assert result["control"].status == "completed"
        assert result["critique"].decision == "approved"
        assert result["errors"] == []
        context = pipeline_models[1].call_args.args[1]
        assert context.evidence.failed_step_ids == ["failed"]
        assert context.evidence.missing_step_ids == ["blocked"]
        assert len(context.evidence.results) == 1
        assert any("failed" in text for text in result["interpretation"].limitations)
        pipeline_models[2].assert_called_once()
    else:
        assert result["errors"][0].source == "analysis"
        assert result["errors"][0].retryable is False
        pipeline_models[1].assert_not_called()
        pipeline_models[2].assert_not_called()


def test_empty_analysis_plan_stops_before_interpretation(
    pipeline_graph: CompiledStateGraph,
    pipeline_dataset: DatasetReference,
    pipeline_plan: Plan,
    pipeline_models: tuple[Mock, Mock, Mock],
) -> None:
    pipeline_plan.analysis_steps = []
    state = create_initial_state("Describe age", pipeline_dataset, max_revisions=0)

    result = pipeline_graph.invoke(state, config={"recursion_limit": 10})

    assert result["analysis_execution_report"].outcome == "failed"
    assert result["errors"][0].code == "INVALID_DATA"
    pipeline_models[1].assert_not_called()
    pipeline_models[2].assert_not_called()


def test_unsupported_evidence_stops_without_calling_models(
    pipeline_graph: CompiledStateGraph,
    pipeline_dataset: DatasetReference,
    pipeline_plan: Plan,
    pipeline_models: tuple[Mock, Mock, Mock],
) -> None:
    pipeline_plan.analysis_steps = [
        PlanStep(
            step_id="group-age",
            tool_name="group_aggregate",
            arguments={
                "group_by": ["score"],
                "aggregations": [
                    {"column": "age", "function": "mean", "alias": "mean_age"}
                ],
            },
        )
    ]
    state = create_initial_state("Describe age", pipeline_dataset, max_revisions=0)

    result = pipeline_graph.invoke(state, config={"recursion_limit": 10})

    assert result["analysis_execution_report"].outcome == "complete"
    assert result["errors"][0].code == "INSUFFICIENT_DATA"
    assert result["errors"][0].source == "interpretation"
    pipeline_models[1].assert_not_called()
    pipeline_models[2].assert_not_called()


@pytest.mark.parametrize(
    "failure", [ValueError("invalid output"), TimeoutError("timeout")]
)
def test_interpretation_failure_clears_old_draft_and_skips_critic(
    pipeline_graph: CompiledStateGraph,
    pipeline_dataset: DatasetReference,
    pipeline_models: tuple[Mock, Mock, Mock],
    failure: Exception,
) -> None:
    pipeline_models[1].side_effect = failure
    state = create_initial_state("Describe age", pipeline_dataset, max_revisions=0)
    state["interpretation"] = Interpretation(summary="Old draft")
    state["critique"] = Critique(decision="approved")

    result = pipeline_graph.invoke(state, config={"recursion_limit": 10})

    assert result["interpretation"] is None
    assert result["critique"] is None
    assert result["errors"][0].source == "interpretation"
    assert result["errors"][0].retryable is isinstance(failure, TimeoutError)
    pipeline_models[1].assert_called_once()
    pipeline_models[2].assert_not_called()


def test_critic_invalid_output_is_recorded_without_retry(
    pipeline_graph: CompiledStateGraph,
    pipeline_dataset: DatasetReference,
    pipeline_models: tuple[Mock, Mock, Mock],
) -> None:
    pipeline_models[2].side_effect = ValueError("Invalid critique")
    state = create_initial_state("Describe age", pipeline_dataset, max_revisions=0)

    result = pipeline_graph.invoke(state, config={"recursion_limit": 10})

    assert result["interpretation"] is not None
    assert result["critique"] is None
    assert result["errors"][0].code == "INVALID_OUTPUT"
    assert result["errors"][0].source == "critic"
    pipeline_models[1].assert_called_once()
    pipeline_models[2].assert_called_once()
