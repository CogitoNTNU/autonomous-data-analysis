"""Malformed review correction belongs to LangGraph and preserves analysis."""

from unittest.mock import Mock

import pytest

from backend.app.contracts.models import Critique
from backend.app.contracts.state import create_initial_state
from backend.app.core.exceptions import ModelOutputError
from backend.app.graph.builder import build_graph
from backend.app.graph.limits import workflow_recursion_limit


@pytest.mark.parametrize("failures", [1, 2])
def test_graph_corrects_output_without_repeating_completed_stages(
    pipeline_dataset,
    pipeline_registry,
    pipeline_models,
    failures,
):
    critic = Mock(
        side_effect=[
            *[
                ModelOutputError("invalid_json", validation_types=["literal_error"])
                for _ in range(failures)
            ],
            Critique(decision="approved"),
        ]
    )
    graph = build_graph(
        pipeline_registry,
        pipeline_models[0],
        interpretation_model=pipeline_models[1],
        critic_model=critic,
    )
    initial = create_initial_state("Describe age", pipeline_dataset, max_retries=0)

    result = graph.invoke(
        initial,
        config={"recursion_limit": workflow_recursion_limit(initial["control"])},
    )

    assert result["control"].status == "completed"
    assert result["control"].revision_count == 0
    assert result["control"].retry_count == 0
    assert result["control"].output_repair_count == failures
    assert len(result["errors"]) == failures
    pipeline_models[0].assert_called_once()
    pipeline_models[1].assert_called_once()
    contexts = [call.args[1] for call in critic.call_args_list]
    assert contexts[0].output_feedback is None
    assert "literal_error" in contexts[1].output_feedback
    assert all(c.analysis_results == contexts[0].analysis_results for c in contexts)
    assert all(c.interpretation == contexts[0].interpretation for c in contexts)


def test_repeated_malformed_reviews_stop_without_approving_or_losing_work(
    pipeline_dataset,
    pipeline_registry,
    pipeline_models,
):
    critic = Mock(side_effect=ModelOutputError("incomplete_response"))
    graph = build_graph(
        pipeline_registry,
        pipeline_models[0],
        interpretation_model=pipeline_models[1],
        critic_model=critic,
    )
    initial = create_initial_state("Describe age", pipeline_dataset, max_retries=0)

    result = graph.invoke(
        initial,
        config={"recursion_limit": workflow_recursion_limit(initial["control"])},
    )

    assert critic.call_count == 3
    assert result["control"].status == "error"
    assert result["control"].output_repair_count == 2
    assert result["critique"] is None
    assert result["interpretation"] is not None
    assert result["analysis_results"]
    assert result["last_node_error"].details["output_reason"] == "incomplete_response"
    pipeline_models[0].assert_called_once()
    pipeline_models[1].assert_called_once()


def test_input_validation_errors_do_not_enter_output_repair(
    pipeline_dataset,
    pipeline_registry,
    pipeline_models,
):
    critic = Mock(side_effect=ValueError("private input failure"))
    graph = build_graph(
        pipeline_registry,
        pipeline_models[0],
        interpretation_model=pipeline_models[1],
        critic_model=critic,
    )

    result = graph.invoke(
        create_initial_state("Describe age", pipeline_dataset),
        config={"recursion_limit": 15},
    )

    critic.assert_called_once()
    assert result["control"].status == "error"
    assert result["control"].output_repair_count == 0
    assert "private" not in result["last_node_error"].message


def test_interleaved_transient_failures_cannot_reset_the_format_budget(
    pipeline_dataset,
    pipeline_registry,
    pipeline_models,
):
    critic = Mock(
        side_effect=[
            ModelOutputError("invalid_json"),
            TimeoutError(),
            ModelOutputError("empty_response"),
            TimeoutError(),
            ModelOutputError("incomplete_response"),
        ]
    )
    graph = build_graph(
        pipeline_registry,
        pipeline_models[0],
        interpretation_model=pipeline_models[1],
        critic_model=critic,
    )
    initial = create_initial_state("Describe age", pipeline_dataset, max_retries=1)

    result = graph.invoke(
        initial,
        config={"recursion_limit": workflow_recursion_limit(initial["control"])},
    )

    assert critic.call_count == 5
    assert result["control"].status == "error"
    assert result["control"].output_repair_count == 2
    assert result["interpretation"] is not None
    assert result["critique"] is None
