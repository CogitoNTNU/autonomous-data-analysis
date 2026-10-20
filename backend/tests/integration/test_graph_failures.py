"""Node boundary failures end the compiled graph with safe diagnostics."""

from unittest.mock import Mock

import pytest
from langgraph.graph.state import CompiledStateGraph

from backend.app.contracts.models import (
    AnalysisUpdates,
    Critique,
    DatasetReference,
    Interpretation,
    InterpretationUpdates,
)
from backend.app.contracts.responses import AgentResponse
from backend.app.contracts.state import create_initial_state


def test_missing_preprocessing_outputs_are_not_silently_accepted(
    pipeline_graph: CompiledStateGraph,
    pipeline_dataset: DatasetReference,
    pipeline_models: tuple[Mock, Mock, Mock],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "backend.app.graph.adapters.preprocessing_node", lambda state: {}
    )
    state = create_initial_state("Describe age", pipeline_dataset, max_revisions=0)

    result = pipeline_graph.invoke(state, config={"recursion_limit": 10})

    assert result["errors"][0].code == "INVALID_OUTPUT"
    assert result["errors"][0].source == "preprocessing"
    assert result["control"].status == "error"
    pipeline_models[1].assert_not_called()
    pipeline_models[2].assert_not_called()


@pytest.mark.parametrize("node", ["analysis", "interpretation"])
def test_success_without_required_output_is_recorded_as_invalid_output(
    pipeline_graph: CompiledStateGraph,
    pipeline_dataset: DatasetReference,
    pipeline_models: tuple[Mock, Mock, Mock],
    monkeypatch: pytest.MonkeyPatch,
    node: str,
) -> None:
    updates = AnalysisUpdates() if node == "analysis" else InterpretationUpdates()
    incomplete_node = Mock(
        return_value=AgentResponse(status="success", updates=updates)
    )
    monkeypatch.setattr(f"backend.app.graph.adapters.{node}_node", incomplete_node)
    state = create_initial_state("Describe age", pipeline_dataset, max_revisions=0)
    if node == "interpretation":
        state["interpretation"] = Interpretation(summary="Old draft")

    result = pipeline_graph.invoke(state, config={"recursion_limit": 10})

    assert len(result["errors"]) == 1
    error = result["errors"][0]
    assert error.code == "INVALID_OUTPUT"
    assert error.source == node
    assert error.retryable is False
    assert result["control"].status == "error"
    assert result["control"].current_agent == node
    assert result["control"].revision_count == 0
    incomplete_node.assert_called_once()
    pipeline_models[1].assert_not_called()
    pipeline_models[2].assert_not_called()
    if node == "interpretation":
        assert result["interpretation"] is None
    else:
        assert result["analysis_execution_report"] is None


def test_revision_without_interpretation_clears_previous_outputs_and_stops(
    pipeline_graph: CompiledStateGraph,
    pipeline_dataset: DatasetReference,
    pipeline_models: tuple[Mock, Mock, Mock],
    revision_critique: Critique,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    interpretation_node = Mock(
        side_effect=[
            AgentResponse[InterpretationUpdates](
                status="success",
                updates=InterpretationUpdates(
                    interpretation=Interpretation(summary="Initial draft")
                ),
            ),
            AgentResponse[InterpretationUpdates](
                status="success", updates=InterpretationUpdates()
            ),
        ]
    )
    monkeypatch.setattr(
        "backend.app.graph.adapters.interpretation_node", interpretation_node
    )
    pipeline_models[2].return_value = revision_critique
    state = create_initial_state("Describe age", pipeline_dataset, max_revisions=2)

    result = pipeline_graph.invoke(state, config={"recursion_limit": 12})

    assert result["interpretation"] is None
    assert result["critique"] is None
    assert result["control"].status == "error"
    assert result["control"].revision_count == 1
    assert len(result["errors"]) == 1
    assert result["errors"][0].code == "INVALID_OUTPUT"
    assert result["errors"][0].source == "interpretation"
    assert interpretation_node.call_count == 2
    pipeline_models[2].assert_called_once()


@pytest.mark.parametrize("node", ["interpretation", "critic"])
@pytest.mark.parametrize("failure", [TimeoutError, ConnectionError, RuntimeError])
def test_model_execution_failures_are_structured_without_retries(
    pipeline_graph: CompiledStateGraph,
    pipeline_dataset: DatasetReference,
    pipeline_models: tuple[Mock, Mock, Mock],
    node: str,
    failure: type[Exception],
) -> None:
    failed_model = pipeline_models[1 if node == "interpretation" else 2]
    failed_model.side_effect = failure("private provider details")
    state = create_initial_state("Describe age", pipeline_dataset, max_revisions=0)
    state["interpretation"] = Interpretation(summary="Old draft")

    result = pipeline_graph.invoke(state, config={"recursion_limit": 10})

    error = result["errors"][0]
    assert error.source == node
    assert "private" not in error.message
    assert error.code == ("TIMEOUT" if failure is TimeoutError else "TOOL_FAILURE")
    assert error.retryable is (failure in (TimeoutError, ConnectionError))
    assert result["critique"] is None
    assert result["control"].status == "error"
    failed_model.assert_called_once()
    if node == "interpretation":
        assert result["interpretation"] is None
        pipeline_models[2].assert_not_called()


def test_missing_critique_is_recorded_as_invalid_output(
    pipeline_graph: CompiledStateGraph,
    pipeline_dataset: DatasetReference,
    pipeline_models: tuple[Mock, Mock, Mock],
) -> None:
    pipeline_models[2].return_value = None
    state = create_initial_state("Describe age", pipeline_dataset, max_revisions=0)

    result = pipeline_graph.invoke(state, config={"recursion_limit": 10})

    assert result["critique"] is None
    assert result["errors"][0].code == "INVALID_OUTPUT"
    assert result["errors"][0].source == "critic"
    assert result["control"].status == "error"
    pipeline_models[2].assert_called_once()
