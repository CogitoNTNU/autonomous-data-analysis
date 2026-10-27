"""Retries recover the current operation without losing revision inputs."""

from dataclasses import replace
from unittest.mock import Mock

import pytest

from backend.app.agents.preprocessing import register_preprocessing_tools
from backend.app.contracts.models import Critique
from backend.app.contracts.state import create_initial_state
from backend.app.graph import nodes
from backend.app.graph.builder import build_graph
from backend.app.graph.limits import workflow_recursion_limit
from backend.app.tools.registry import ToolRegistry


@pytest.mark.parametrize(
    "agent", ["planner", "preprocessing", "analysis", "interpretation", "critic"]
)
def test_transient_failure_retries_only_the_failed_node(
    pipeline_graph, pipeline_dataset, monkeypatch, agent
):
    original = getattr(nodes, f"{agent}_node")
    calls = 0

    def fail_once(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise TimeoutError("private provider details")
        return original(*args, **kwargs)

    monkeypatch.setattr(nodes, f"{agent}_node", fail_once)
    state = create_initial_state("Describe age", pipeline_dataset, max_retries=1)
    events = list(
        pipeline_graph.stream(
            state,
            stream_mode="updates",
            config={"recursion_limit": workflow_recursion_limit(state["control"])},
        )
    )
    path = [name for event in events for name in event]
    result = {**state}
    for event in events:
        for update in event.values():
            result.update(update)

    assert result["control"].status == "completed"
    assert result["last_node_error"] is None
    assert len(result["errors"]) == 1
    assert result["errors"][0].code == "TIMEOUT"
    assert "private" not in result["errors"][0].message
    for name in ["planner", "preprocessing", "analysis", "interpretation", "critic"]:
        assert path.count(name) == (2 if name == agent else 1)


@pytest.mark.parametrize("max_retries", [0, 1, 2])
def test_retry_budget_stops_repeated_failures(
    pipeline_graph, pipeline_dataset, pipeline_models, max_retries
):
    critic = pipeline_models[2]
    critic.side_effect = ConnectionError("private")
    state = create_initial_state(
        "Describe age", pipeline_dataset, max_retries=max_retries
    )

    result = pipeline_graph.invoke(state, config={"recursion_limit": 20})

    assert critic.call_count == max_retries + 1
    assert result["control"].status == "error"
    assert result["control"].retry_count == max_retries
    assert result["last_node_error"].retryable
    assert len(result["errors"]) == max_retries + 1
    assert result["critique"] is None


def test_revision_retry_preserves_feedback_and_counts_one_revision(
    pipeline_graph, pipeline_dataset, pipeline_models, revision_critique
):
    interpretation, critic = pipeline_models[1:]
    interpret = interpretation.side_effect

    def fail_on_first_revision(prompt, context):
        if interpretation.call_count == 2:
            raise TimeoutError("temporary")
        return interpret(prompt, context)

    interpretation.side_effect = fail_on_first_revision
    critic.side_effect = [revision_critique, Critique(decision="approved")]
    state = create_initial_state(
        "Describe age", pipeline_dataset, max_revisions=1, max_retries=1
    )

    result = pipeline_graph.invoke(state, config={"recursion_limit": 20})

    assert result["control"].status == "completed"
    assert result["control"].revision_count == 1
    assert interpretation.call_count == 3
    assert (
        interpretation.call_args_list[1].args[1]
        == interpretation.call_args_list[2].args[1]
    )
    assert interpretation.call_args_list[2].args[1].revision_feedback
    assert len(result["revision_history"]) == 1


@pytest.mark.parametrize(
    "agent", ["planner", "preprocessing", "analysis", "interpretation", "critic"]
)
def test_permanent_failures_never_retry(
    pipeline_graph, pipeline_dataset, monkeypatch, agent
):
    failing = Mock(side_effect=ValueError("invalid input"))
    monkeypatch.setattr(nodes, f"{agent}_node", failing)
    state = create_initial_state("Describe age", pipeline_dataset, max_retries=2)

    result = pipeline_graph.invoke(state, config={"recursion_limit": 15})

    failing.assert_called_once()
    assert result["control"].status == "error"
    assert not result["last_node_error"].retryable


def test_real_analysis_executor_preserves_transient_failure_classification(
    pipeline_dataset, pipeline_models, pipeline_registry
):
    tool = pipeline_registry.get("descriptive_statistics")
    calls = 0

    def fail_once(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ConnectionError("temporary")
        return tool.run(*args, **kwargs)

    registry = register_preprocessing_tools(ToolRegistry())
    registry.register(replace(tool, run=fail_once))
    planner, interpretation, critic = pipeline_models
    graph = build_graph(
        registry, planner, interpretation_model=interpretation, critic_model=critic
    )
    state = create_initial_state("Describe age", pipeline_dataset, max_retries=1)

    result = graph.invoke(state, config={"recursion_limit": 15})

    assert calls == 2
    assert result["control"].status == "completed"
    assert result["analysis_execution_report"].outcome == "complete"
    assert result["errors"][0].retryable
    planner.assert_called_once()
    interpretation.assert_called_once()


def test_retry_budget_resets_for_each_operation(
    pipeline_graph, pipeline_dataset, pipeline_models
):
    interpret = pipeline_models[1].side_effect
    calls = 0

    def fail_once(prompt, context):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise TimeoutError("temporary")
        return interpret(prompt, context)

    pipeline_models[1].side_effect = fail_once
    pipeline_models[2].side_effect = [
        TimeoutError("temporary"),
        Critique(decision="approved"),
    ]
    state = create_initial_state("Describe age", pipeline_dataset, max_retries=1)

    result = pipeline_graph.invoke(state, config={"recursion_limit": 15})

    assert result["control"].status == "completed"
    assert len(result["errors"]) == 2
    assert pipeline_models[2].call_count == 2
    assert len(result["warnings"]) == len(
        {warning.model_dump_json() for warning in result["warnings"]}
    )


def test_recursion_budget_covers_retries_during_an_upstream_revision(
    pipeline_graph, pipeline_dataset, pipeline_models, revision_critique, monkeypatch
):
    revision_critique.issues[0].target_agent = "planner"
    pipeline_models[2].side_effect = [revision_critique, Critique(decision="approved")]
    calls = {}

    def with_transient_failures(name, original):
        def run(*args, **kwargs):
            calls[name] = calls.get(name, 0) + 1
            if calls[name] % 2:
                raise TimeoutError("temporary")
            return original(*args, **kwargs)

        return run

    for name in ["planner", "preprocessing", "analysis", "interpretation", "critic"]:
        monkeypatch.setattr(
            nodes,
            f"{name}_node",
            with_transient_failures(name, getattr(nodes, f"{name}_node")),
        )
    state = create_initial_state(
        "Describe age", pipeline_dataset, max_revisions=1, max_retries=1
    )

    result = pipeline_graph.invoke(
        state, config={"recursion_limit": workflow_recursion_limit(state["control"])}
    )

    assert result["control"].status == "completed"
    assert result["control"].revision_count == 1
    assert len(result["revision_history"]) == 1
    assert len(result["errors"]) == 10
    assert set(calls.values()) == {4}
