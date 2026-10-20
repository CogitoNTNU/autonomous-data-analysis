"""Warning projections do not create additional events in graph state."""

from unittest.mock import Mock

import pytest
from langgraph.graph.state import CompiledStateGraph

from backend.app.contracts.models import (
    Critique,
    DatasetReference,
    Plan,
    PlanStep,
    PreprocessingReport,
    WarningEvent,
)
from backend.app.contracts.state import AgentState, create_initial_state
from backend.app.graph import adapters


@pytest.mark.parametrize("outcome", ["approved", "revised", "interpretation_failed"])
def test_partial_analysis_preserves_distinct_original_warnings_without_sanitized_copies(
    pipeline_graph: CompiledStateGraph,
    pipeline_dataset: DatasetReference,
    pipeline_plan: Plan,
    pipeline_models: tuple[Mock, Mock, Mock],
    revision_critique: Critique,
    monkeypatch: pytest.MonkeyPatch,
    outcome: str,
) -> None:
    pipeline_plan.analysis_steps.append(
        PlanStep(
            step_id="failed",
            tool_name="failing_statistics",
            arguments={"columns": ["age"]},
        )
    )
    prior_warning = WarningEvent(
        code="TOOL_FAILURE",
        source="analysis",
        step_id="failed",
        message="A different private diagnostic for the same step.",
    )
    preprocessing_warnings = [
        WarningEvent(
            code="PREPROCESSING_WARNING", source="preprocessing", message=message
        )
        for message in (
            "A preprocessing limitation.",
            "A different preprocessing limitation.",
        )
    ]
    original_preprocessing = adapters.preprocessing_node

    def preprocess(state: AgentState) -> dict[str, object]:
        updates = original_preprocessing(state)
        report = updates["preprocessing_report"]
        assert isinstance(report, PreprocessingReport)
        report.warnings.extend(preprocessing_warnings)
        return updates

    monkeypatch.setattr(adapters, "preprocessing_node", preprocess)
    if outcome == "revised":
        pipeline_models[2].side_effect = [
            revision_critique,
            Critique(decision="approved"),
        ]
    elif outcome == "interpretation_failed":
        pipeline_models[1].side_effect = ValueError("Invalid draft")
    state = create_initial_state("Describe age", pipeline_dataset, max_revisions=1)
    state["warnings"] = [prior_warning]

    result = pipeline_graph.invoke(state, config={"recursion_limit": 12})

    assert result["analysis_execution_report"].outcome == "partial"
    expected = [
        prior_warning,
        *(
            warning
            for analysis in result["analysis_results"]
            for warning in analysis.warnings
        ),
        *preprocessing_warnings,
    ]
    assert result["warnings"] == expected
    failures = [
        warning for warning in result["warnings"] if warning.code == "TOOL_FAILURE"
    ]
    assert [warning.message for warning in failures] == [
        prior_warning.message,
        "Tool could not complete",
    ]
    assert state["warnings"] == [prior_warning]
    if outcome == "interpretation_failed":
        assert result["errors"][0].source == "interpretation"
        pipeline_models[2].assert_not_called()
    else:
        assert result["errors"] == []
        assert result["critique"].decision == "approved"
        for call in pipeline_models[1].call_args_list:
            assert all(
                "private" not in warning.message
                for warning in call.args[1].evidence.warnings
            )
