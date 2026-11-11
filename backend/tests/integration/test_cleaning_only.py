"""Cleaning requests complete without inventing analysis results."""

from unittest.mock import Mock, patch

import pytest

from backend.app.agents.analysis.node import analysis_node
from backend.app.agents.planner.schema import PlannerOutput
from backend.app.agents.preprocessing import register_preprocessing_tools
from backend.app.contracts.models import (
    Critique,
    DatasetReference,
    Interpretation,
    Plan,
    PlanStep,
    PreprocessingReport,
)
from backend.app.contracts.state import create_initial_state
from backend.app.graph.builder import build_graph
from backend.app.tools.analysis.descriptive import default_registry


def cleaning_plan() -> Plan:
    return Plan(
        plan_id="clean",
        objective="Remove duplicate rows.",
        preprocessing_steps=[PlanStep(step_id="dedupe", tool_name="remove_duplicates")],
    )


def test_cleaning_report_reaches_interpretation_and_critic_without_analysis() -> None:
    dataset = DatasetReference(
        dataset_id="data",
        version="raw",
        storage_ref="registered.csv",
        schema={"age": {"datatype": "integer"}},
    )
    processed = dataset.model_copy(update={"version": "clean"})
    report = PreprocessingReport(
        rows_before=3, rows_after=2, changes=["Removed one duplicate."]
    )
    interpretation = Mock(
        return_value=Interpretation(summary="Removed one duplicate; two rows remain.")
    )
    graph = build_graph(
        register_preprocessing_tools(default_registry()),
        Mock(return_value=PlannerOutput(plan=cleaning_plan())),
        interpretation_model=interpretation,
        critic_model=Mock(return_value=Critique(decision="approved")),
    )

    with patch(
        "backend.app.agents.preprocessing.workflow.run_shared_preprocessing",
        return_value=(processed, report),
    ):
        result = graph.invoke(
            create_initial_state("Remove duplicate rows.", dataset),
            config={"recursion_limit": 10},
        )

    assert result["control"].status == "completed", result["errors"]
    assert result["errors"] == []
    assert result["analysis_results"] == []
    assert result["analysis_execution_report"].outcome == "not_required"
    context = interpretation.call_args.args[1]
    assert context.preprocessing_report == report
    assert context.evidence.results == []
    assert result["critique"].decision == "approved"


@pytest.mark.parametrize("has_preprocessing", [True, False])
def test_empty_analysis_without_completed_cleaning_still_fails(
    has_preprocessing: bool,
) -> None:
    dataset = DatasetReference(
        dataset_id="data", version="raw", storage_ref="registered.csv", schema={}
    )
    state = create_initial_state("Clean data", dataset)
    state["processed_dataset"] = dataset
    state["plan"] = (
        cleaning_plan()
        if has_preprocessing
        else Plan(plan_id="empty", objective="Clean data")
    )

    response = analysis_node(state)

    assert response.status == "error"
    assert response.error.code == "INVALID_DATA"
