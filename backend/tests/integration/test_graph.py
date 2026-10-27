"""Test graph routing and deterministic execution without calling an LLM."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from backend.app.agents.planner.schema import ClarificationRequest, PlannerOutput
from backend.app.contracts.models import (
    Critique,
    DatasetReference,
    Finding,
    Interpretation,
    Plan,
    PlanStep,
)
from backend.app.contracts.state import create_initial_state
from backend.app.graph.builder import build_graph
from backend.app.tools.analysis.descriptive import default_registry


@pytest.mark.parametrize("outcome", ["success", "clarification", "invalid_plan"])
def test_planner_graph_merges_model_outcome_into_state(outcome: str) -> None:
    dataset = DatasetReference(
        dataset_id="ages",
        version="v1",
        storage_ref="unused.csv",
        schema={"age": {"datatype": "integer"}},
    )
    plan = Plan(
        plan_id="describe-ages",
        objective="Describe age.",
        required_columns=["missing" if outcome == "invalid_plan" else "age"],
        analysis_steps=[
            PlanStep(
                step_id="describe-age",
                tool_name="descriptive_statistics",
                arguments={"columns": ["age"]},
            )
        ],
    )
    question = "Which age group should be described?"
    output = (
        PlannerOutput(clarification=ClarificationRequest(question=question))
        if outcome == "clarification"
        else PlannerOutput(plan=plan)
    )
    model = Mock(return_value=output)
    initial_state = create_initial_state(
        "Describe age.", dataset, run_id="graph-test", max_revisions=0
    )
    with patch(
        "backend.app.graph.builder.preprocessing_graph_node",
        return_value={},
    ) as preprocessing:
        interpretation_model = Mock()
        graph = build_graph(
            registry=default_registry(),
            planner_model=model,
            interpretation_model=interpretation_model,
            critic_model=Mock(return_value=Critique(decision="approved")),
        )
        result = graph.invoke(initial_state, config={"recursion_limit": 8})

    if outcome == "success":
        preprocessing.assert_called_once()
    else:
        preprocessing.assert_not_called()

    interpretation_model.assert_not_called()
    model.assert_called_once()
    context = model.call_args.args[1]
    assert context.user_query == initial_state["user_query"]
    assert context.dataset == dataset
    assert result["run_id"] == "graph-test"
    assert result["dataset"] == dataset
    assert result["analysis_results"] == []
    if outcome == "success":
        assert result["plan"] == plan
        # This routing stub intentionally supplies no preprocessing output.
        assert result["control"].status == "error"
        assert len(result["errors"]) == 1
        assert result["errors"][0].source == "harness"
        assert result["clarification_question"] is None
    elif outcome == "clarification":
        assert result["plan"] is None
        assert result["errors"] == []
        assert result["clarification_question"] == question
        assert result["control"].status == "needs_clarification"
    else:
        assert result["plan"] is None
        assert result["clarification_question"] is None
        assert len(result["errors"]) == 1
        assert result["errors"][0].code == "INVALID_OUTPUT"
        assert result["errors"][0].source == "planner"
        assert "missing" in result["errors"][0].message


@pytest.mark.parametrize("node_name", ["preprocessing", "analysis"])
def test_executor_node_accepts_state(node_name: str) -> None:
    dataset = DatasetReference(
        dataset_id="ages",
        version="v1",
        storage_ref="unused.csv",
        schema={"age": {"datatype": "integer"}},
    )
    state = create_initial_state("Describe age.", dataset)
    model = Mock()
    graph = build_graph(
        registry=default_registry(),
        planner_model=model,
        interpretation_model=Mock(),
        critic_model=Mock(),
    )

    result = graph.nodes[node_name].invoke(state)

    if node_name == "analysis":
        assert len(result["errors"]) == 1
        assert result["errors"][0].code == "INVALID_DATA"
        assert result["errors"][0].source == "analysis"
        assert result["analysis_results"] == []
    else:
        assert len(result["errors"]) == 1
        assert result["errors"][0].code == "INVALID_DATA"
        assert result["errors"][0].source == "preprocessing"
        assert result["processed_dataset"] is None
    model.assert_not_called()


def test_graph_runs_through_interpretation_on_real_dataset():
    path = Path(__file__).resolve().parents[1] / "fixtures" / "clean.csv"
    original_csv = path.read_bytes()
    dataset = DatasetReference(
        dataset_id="ages",
        version="v1",
        storage_ref=str(path),
        schema={"age": {"datatype": "integer"}},
    )
    plan = Plan(
        plan_id="describe-ages",
        objective="Describe age.",
        required_columns=["age"],
        analysis_steps=[
            PlanStep(
                step_id="describe-age",
                tool_name="descriptive_statistics",
                arguments={"columns": ["age"]},
            ),
        ],
    )
    model = Mock(return_value=PlannerOutput(plan=plan))
    state = create_initial_state("Describe age.", dataset)

    def interpret(prompt, context):
        evidence = context.evidence.results[0]
        return Interpretation(
            summary="Observed age summary.",
            findings=[
                Finding(
                    claim="Mean age is 20.0 across 3 observations.",
                    result_ids=[evidence.result_id],
                ),
            ],
        )

    interpretation_model = Mock(side_effect=interpret)
    graph = build_graph(
        registry=default_registry(),
        planner_model=model,
        interpretation_model=interpretation_model,
        critic_model=Mock(return_value=Critique(decision="approved")),
    )

    result = graph.invoke(state, config={"recursion_limit": 10})

    model.assert_called_once()
    assert result["errors"] == []
    processed = result["processed_dataset"]
    assert processed.dataset_id == dataset.dataset_id
    assert processed.version == dataset.version
    assert Path(processed.storage_ref) == path
    assert result["preprocessing_report"].rows_before == 3
    assert result["preprocessing_report"].rows_after == 3
    report = result["analysis_execution_report"]
    assert report.outcome == "complete"
    assert report.completed_step_ids == ["describe-age"]
    assert len(result["analysis_results"]) == 1
    analysis = result["analysis_results"][0]
    assert analysis.step_id == "describe-age"
    assert analysis.dataset_version == "v1"
    assert analysis.sample_size == 3
    assert analysis.values["columns"]["age"]["mean"] == 20.0
    interpretation_model.assert_called_once()
    assert result["control"].status == "completed"
    assert result["interpretation"] is not None
    assert result["interpretation"].findings[0].result_ids == [analysis.result_id]
    assert any(
        "LOW_SAMPLE_SIZE" in text for text in result["interpretation"].limitations
    )
    assert path.read_bytes() == original_csv


@pytest.mark.parametrize(
    "exception", [FileNotFoundError(), PermissionError(), ValueError()]
)
def test_graph_stops_before_analysis_on_preprocessing_failure(exception):
    dataset = DatasetReference(
        dataset_id="ages",
        version="v1",
        storage_ref="unused.csv",
        schema={"age": {"datatype": "integer"}},
    )
    plan = Plan(plan_id="plan-1", objective="Describe age.")
    planner_model = Mock(return_value=PlannerOutput(plan=plan))
    interpretation_model = Mock()
    state = create_initial_state("Describe age.", dataset)

    with (
        patch(
            "backend.app.agents.preprocessing.workflow.run_shared_preprocessing",
            side_effect=exception,
        ),
        patch("backend.app.graph.builder.analysis_graph_node") as analysis,
    ):
        graph = build_graph(
            registry=default_registry(),
            planner_model=planner_model,
            interpretation_model=interpretation_model,
            critic_model=Mock(return_value=Critique(decision="approved")),
        )
        result = graph.invoke(state, config={"recursion_limit": 10})

    assert len(result["errors"]) == 1
    assert result["errors"][0].source == "preprocessing"
    assert result["processed_dataset"] is None
    assert result["analysis_results"] == []
    analysis.assert_not_called()
    interpretation_model.assert_not_called()
