"""Bounded Critic feedback revises Interpretation through the compiled graph."""

from unittest.mock import Mock

import pytest
from langgraph.graph.state import CompiledStateGraph

from backend.app.agents.interpretation.schema import InterpretationContext
from backend.app.contracts.models import (
    Critique,
    CritiqueIssue,
    DatasetReference,
    Interpretation,
)
from backend.app.contracts.state import create_initial_state
from backend.app.graph import nodes


@pytest.mark.parametrize(
    "max_revisions,revisions", [(2, 0), (2, 1), (3, 2), (2, 2), (4, 4)]
)
def test_revisions_pass_feedback_without_reexecuting_upstream_nodes(
    pipeline_graph: CompiledStateGraph,
    pipeline_dataset: DatasetReference,
    pipeline_models: tuple[Mock, Mock, Mock],
    revision_critique: Critique,
    monkeypatch: pytest.MonkeyPatch,
    max_revisions: int,
    revisions: int,
) -> None:
    planner, interpretation, critic = pipeline_models
    initial_interpret = interpretation.side_effect

    def interpret(prompt: str, context: InterpretationContext) -> Interpretation:
        draft = initial_interpret(prompt, context)
        return draft.model_copy(
            update={"summary": f"Draft {interpretation.call_count}"}
        )

    interpretation.side_effect = interpret
    preprocessing = Mock(wraps=nodes.preprocessing_node)
    analysis = Mock(wraps=nodes.analysis_node)
    review = Mock(wraps=nodes.critic_node)
    monkeypatch.setattr(nodes, "preprocessing_node", preprocessing)
    monkeypatch.setattr(nodes, "analysis_node", analysis)
    monkeypatch.setattr(nodes, "critic_node", review)
    feedback = [revision_critique.model_copy(deep=True) for _ in range(revisions)]
    for index, critique in enumerate(feedback):
        critique.issues[0].description += f" Review {index + 1}."
    critic.side_effect = [*feedback, Critique(decision="approved")]
    state = create_initial_state(
        "Describe age", pipeline_dataset, max_revisions=max_revisions
    )

    result = pipeline_graph.invoke(state, config={"recursion_limit": 20})

    assert result["critique"].decision == "approved"
    assert result["control"].status == "completed"
    assert result["control"].revision_count == revisions
    assert result["errors"] == []
    assert interpretation.call_count == critic.call_count == revisions + 1
    planner.assert_called_once()
    preprocessing.assert_called_once()
    analysis.assert_called_once()
    initial = interpretation.call_args_list[0].args[1]
    assert initial.previous_interpretation is None
    assert initial.revision_feedback == []
    for index in range(1, revisions + 1):
        context = interpretation.call_args_list[index].args[1]
        assert (
            context.previous_interpretation
            == critic.call_args_list[index - 1].args[1].interpretation
        )
        assert context.revision_feedback == [
            feedback[index - 1].issues[0].description,
            *feedback[index - 1].required_changes,
        ]
        assert context.evidence == initial.evidence
    for call in review.call_args_list:
        assert call.args[0]["critique"] is None
    assert state["control"].revision_count == 0
    assert state["control"].status == "pending"
    assert state["critique"] is None
    assert result["interpretation"].summary == f"Draft {revisions + 1}"


@pytest.mark.parametrize("max_revisions", [0, 1, 2])
def test_revision_limit_terminates_repeated_rejections(
    pipeline_graph: CompiledStateGraph,
    pipeline_dataset: DatasetReference,
    pipeline_models: tuple[Mock, Mock, Mock],
    revision_critique: Critique,
    max_revisions: int,
) -> None:
    pipeline_models[2].return_value = revision_critique
    state = create_initial_state(
        "Describe age", pipeline_dataset, max_revisions=max_revisions
    )

    result = pipeline_graph.invoke(state, config={"recursion_limit": 15})

    assert result["critique"] == revision_critique
    assert result["control"].status == "error"
    assert result["control"].revision_count == max_revisions
    assert result["errors"][0].code == "REVISION_LIMIT"
    assert result["errors"][0].retryable is False
    assert result["errors"][0].details["max_revisions"] == max_revisions
    assert (
        pipeline_models[1].call_count
        == pipeline_models[2].call_count
        == max_revisions + 1
    )


def test_cannot_complete_preserves_the_structured_blocker(
    pipeline_graph: CompiledStateGraph,
    pipeline_dataset: DatasetReference,
    pipeline_models: tuple[Mock, Mock, Mock],
) -> None:
    critique = Critique(
        decision="cannot_complete",
        required_changes=["The requested comparison requires an unavailable dataset."],
    )
    pipeline_models[2].return_value = critique
    state = create_initial_state("Describe age", pipeline_dataset, max_revisions=2)

    result = pipeline_graph.invoke(state, config={"recursion_limit": 10})

    assert result["critique"] == critique
    assert result["control"].status == "error"
    assert result["control"].revision_count == 0
    error = result["errors"][0]
    assert error.code == "INSUFFICIENT_DATA"
    assert error.details["decision"] == "cannot_complete"
    assert error.details["required_changes"] == critique.required_changes
    pipeline_models[1].assert_called_once()
    pipeline_models[2].assert_called_once()


@pytest.mark.parametrize(
    "targets",
    [
        ["critic"],
        ["chat"],
        ["interpretation", "chat"],
    ],
)
def test_unsupported_revision_targets_do_not_reach_interpretation(
    pipeline_graph: CompiledStateGraph,
    pipeline_dataset: DatasetReference,
    pipeline_models: tuple[Mock, Mock, Mock],
    revision_critique: Critique,
    targets: list[str],
) -> None:
    revision_critique.issues = [
        CritiqueIssue(
            code="UPSTREAM_CHANGE",
            severity="error",
            description="Change the method.",
            target_agent=target,
        )
        for target in targets
    ]
    pipeline_models[2].return_value = revision_critique
    state = create_initial_state("Describe age", pipeline_dataset, max_revisions=2)

    result = pipeline_graph.invoke(state, config={"recursion_limit": 10})

    error = result["errors"][0]
    assert error.code == "INVALID_OUTPUT"
    assert error.details["reason"] == "unsupported_revision_targets"
    assert error.details["target_agents"] == sorted(set(targets) - {"interpretation"})
    assert result["control"].status == "error"
    assert result["control"].revision_count == 0
    pipeline_models[0].assert_called_once()
    pipeline_models[1].assert_called_once()
    pipeline_models[2].assert_called_once()


@pytest.mark.parametrize("empty_issues", [True, False])
def test_revision_requires_an_actionable_targeted_issue(
    pipeline_graph: CompiledStateGraph,
    pipeline_dataset: DatasetReference,
    pipeline_models: tuple[Mock, Mock, Mock],
    revision_critique: Critique,
    empty_issues: bool,
) -> None:
    if empty_issues:
        revision_critique.issues = []
    else:
        revision_critique.issues[0].description = "   "
    pipeline_models[2].return_value = revision_critique
    state = create_initial_state("Describe age", pipeline_dataset, max_revisions=2)

    result = pipeline_graph.invoke(state, config={"recursion_limit": 10})

    assert result["errors"][0].code == "INVALID_OUTPUT"
    assert result["errors"][0].details["reason"] == "missing_actionable_feedback"
    assert result["control"].revision_count == 0
    pipeline_models[1].assert_called_once()
    pipeline_models[2].assert_called_once()


@pytest.mark.parametrize("node", ["interpretation", "critic"])
@pytest.mark.parametrize("failure", [ValueError, TimeoutError, RuntimeError])
def test_failed_revision_does_not_reuse_previous_outputs(
    pipeline_graph: CompiledStateGraph,
    pipeline_dataset: DatasetReference,
    pipeline_models: tuple[Mock, Mock, Mock],
    revision_critique: Critique,
    node: str,
    failure: type[Exception],
) -> None:
    interpretation, critic = pipeline_models[1:]
    if node == "interpretation":
        initial_interpret = interpretation.side_effect

        def interpret(prompt: str, context: InterpretationContext) -> Interpretation:
            if interpretation.call_count == 2:
                raise failure("private provider details")
            return initial_interpret(prompt, context)

        interpretation.side_effect = interpret
        critic.side_effect = [revision_critique]
    else:
        critic.side_effect = [revision_critique, failure("private provider details")]
    state = create_initial_state(
        "Describe age", pipeline_dataset, max_revisions=2, max_retries=0
    )

    result = pipeline_graph.invoke(state, config={"recursion_limit": 16})

    assert result["control"].status == "error"
    assert result["control"].revision_count == 1
    assert result["critique"] is None
    assert result["errors"][0].source == node
    assert "private" not in result["errors"][0].message
    assert interpretation.call_count == 2
    assert critic.call_count == (1 if node == "interpretation" else 2)
    if node == "interpretation":
        assert result["interpretation"] is None


def test_missing_critique_after_revision_does_not_reuse_feedback(
    pipeline_graph: CompiledStateGraph,
    pipeline_dataset: DatasetReference,
    pipeline_models: tuple[Mock, Mock, Mock],
    revision_critique: Critique,
) -> None:
    pipeline_models[2].side_effect = [revision_critique, None]
    state = create_initial_state("Describe age", pipeline_dataset, max_revisions=2)

    result = pipeline_graph.invoke(state, config={"recursion_limit": 12})

    assert result["critique"] is None
    assert result["errors"][0].code == "INVALID_OUTPUT"
    assert result["control"].status == "error"
    assert result["control"].revision_count == 1
    assert pipeline_models[1].call_count == pipeline_models[2].call_count == 2
