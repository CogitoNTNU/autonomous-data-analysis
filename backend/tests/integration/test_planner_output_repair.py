"""The harness corrects generated Planner format failures before execution."""

from unittest.mock import Mock

import pytest

from backend.app.contracts.models import Critique
from backend.app.contracts.state import create_initial_state
from backend.app.core.exceptions import ModelOutputError
from backend.app.graph.builder import build_graph
from backend.app.graph.limits import workflow_recursion_limit


@pytest.mark.parametrize(
    "reason",
    ["invalid_json", "incomplete_response", "empty_response", "invalid_envelope"],
)
def test_planner_output_correction_keeps_request_and_executes_only_valid_plan(
    pipeline_dataset,
    pipeline_registry,
    pipeline_models,
    reason,
):
    planner = Mock(
        side_effect=[ModelOutputError(reason), pipeline_models[0].return_value]
    )
    graph = build_graph(
        pipeline_registry,
        planner,
        interpretation_model=pipeline_models[1],
        critic_model=pipeline_models[2],
    )
    initial = create_initial_state("Describe age", pipeline_dataset, max_retries=0)

    result = graph.invoke(
        initial,
        config={"recursion_limit": workflow_recursion_limit(initial["control"])},
    )

    assert result["control"].status == "completed"
    assert planner.call_count == 2
    first, second = [call.args[1] for call in planner.call_args_list]
    assert second.user_query == first.user_query
    assert second.dataset == first.dataset
    assert first.output_feedback is None
    assert reason in second.output_feedback
    assert "PlannerOutput" in second.output_feedback
    assert result["control"].revision_count == 0
    assert result["errors"][0].details["output_reason"] == reason
    pipeline_models[1].assert_called_once()
    pipeline_models[2].assert_called_once()


def test_repeated_invalid_planner_output_stops_before_any_execution(
    pipeline_dataset,
    pipeline_registry,
    pipeline_models,
):
    planner = Mock(side_effect=ModelOutputError("invalid_json"))
    graph = build_graph(
        pipeline_registry,
        planner,
        interpretation_model=pipeline_models[1],
        critic_model=pipeline_models[2],
    )
    initial = create_initial_state("Describe age", pipeline_dataset, max_retries=0)

    result = graph.invoke(
        initial,
        config={"recursion_limit": workflow_recursion_limit(initial["control"])},
    )

    assert result["control"].status == "error"
    assert planner.call_count == 3
    assert result["control"].output_repair_count == 2
    assert result["plan"] is None
    assert result["preprocessing_report"] is None
    assert not result["analysis_results"]
    pipeline_models[1].assert_not_called()
    pipeline_models[2].assert_not_called()


def test_invalid_plan_dependencies_are_not_repeated_as_format_correction(
    pipeline_dataset,
    pipeline_registry,
    pipeline_models,
    pipeline_plan,
):
    invalid = pipeline_plan.model_copy(deep=True)
    invalid.analysis_steps[0].depends_on = ["unknown-step"]
    pipeline_models[0].return_value.plan = invalid
    graph = build_graph(
        pipeline_registry,
        pipeline_models[0],
        interpretation_model=pipeline_models[1],
        critic_model=pipeline_models[2],
    )

    result = graph.invoke(
        create_initial_state("Describe age", pipeline_dataset),
        config={"recursion_limit": 20},
    )

    pipeline_models[0].assert_called_once()
    assert result["control"].status == "error"
    assert result["control"].output_repair_count == 0
    assert result["preprocessing_report"] is None


def test_planner_and_critic_have_separate_stage_correction_budgets(
    pipeline_dataset,
    pipeline_registry,
    pipeline_models,
):
    planner = Mock(
        side_effect=[ModelOutputError("invalid_json"), pipeline_models[0].return_value]
    )
    critic = Mock(
        side_effect=[ModelOutputError("empty_response"), Critique(decision="approved")]
    )
    graph = build_graph(
        pipeline_registry,
        planner,
        interpretation_model=pipeline_models[1],
        critic_model=critic,
    )
    initial = create_initial_state(
        "Describe age", pipeline_dataset, max_output_repairs=1, max_retries=0
    )

    result = graph.invoke(
        initial,
        config={"recursion_limit": workflow_recursion_limit(initial["control"])},
    )

    assert result["control"].status == "completed"
    assert planner.call_count == critic.call_count == 2
    assert result["control"].output_repair_count == 1
    assert len(result["errors"]) == 2
