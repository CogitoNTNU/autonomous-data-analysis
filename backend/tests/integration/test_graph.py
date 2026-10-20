"""Run the real Planner graph without calling an LLM or reading datasets."""

from unittest.mock import Mock, patch

import pytest

from backend.app.agents.planner.schema import ClarificationRequest, PlannerOutput
from backend.app.contracts.models import DatasetReference, Plan, PlanStep
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
        "backend.app.graph.builder.preprocessing_node",
        return_value={},
    ) as preprocessing:
        graph = build_graph(registry=default_registry(), planner_model=model)
        result = graph.invoke(initial_state, config={"recursion_limit": 5})

    if outcome == "success":
        preprocessing.assert_called_once()
    else:
        preprocessing.assert_not_called()

    model.assert_called_once()
    context = model.call_args.args[1]
    assert context.user_query == initial_state["user_query"]
    assert context.dataset == dataset
    assert result["run_id"] == "graph-test"
    assert result["dataset"] == dataset
    assert result["analysis_results"] == []
    if outcome == "success":
        assert result["plan"] == plan
        assert result["errors"] == []
        assert result["clarification_question"] is None
    elif outcome == "clarification":
        assert result["plan"] is None
        assert result["errors"] == []
        assert result["clarification_question"] == question
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
    graph = build_graph(registry=default_registry(), planner_model=model)

    result = graph.nodes[node_name].invoke(state)

    if node_name == "analysis":
        assert len(result["errors"]) == 1
        assert result["errors"][0].code == "INVALID_DATA"
        assert result["errors"][0].source == "analysis"
        assert result["analysis_results"] == []
    else:
        assert len(result["warnings"]) == 1
        warning = result["warnings"][0]
        assert warning.code == "INVALID_DATA"
        assert warning.source == "preprocessing"
    model.assert_not_called()
