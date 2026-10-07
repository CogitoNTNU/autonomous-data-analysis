"""Interpretation reads only its state inputs and returns typed updates."""

from copy import deepcopy
from unittest.mock import Mock

import pytest

from backend.app.agents.interpretation import (
    build_interpretation_input,
    interpretation_node,
)
from backend.app.contracts.models import (
    AnalysisResult,
    Critique,
    CritiqueIssue,
    DatasetReference,
    Finding,
    Interpretation,
    Plan,
    PlanStep,
)
from backend.app.contracts.responses import AgentResponse
from backend.app.contracts.state import AgentState, create_initial_state


@pytest.fixture
def state() -> AgentState:
    dataset = DatasetReference(
        dataset_id="ages",
        version="raw-v1",
        storage_ref="unused.csv",
        schema={"age": {"datatype": "integer"}},
    )
    state = create_initial_state("Describe age", dataset, run_id="run1")
    state["processed_dataset"] = dataset.model_copy(update={"version": "processed-v1"})
    state["plan"] = Plan(
        plan_id="p1",
        objective="Summarize age",
        analysis_steps=[
            PlanStep(
                step_id="s1",
                tool_name="descriptive_statistics",
                arguments={"columns": ["age"]},
            ),
        ],
    )
    state["analysis_results"] = [
        AnalysisResult(
            result_id="r1",
            step_id="s1",
            dataset_version="processed-v1",
            method="descriptive_statistics",
            parameters={"columns": ["age"]},
            sample_size=3,
            values={
                "status": "ok",
                "columns": {
                    "age": {
                        "mean": 2.0,
                        "median": 2.0,
                        "std": 1.0,
                        "min": 1.0,
                        "max": 3.0,
                        "n": 3,
                        "missing_rate": 0.0,
                    }
                },
            },
        )
    ]
    return state


@pytest.fixture
def draft() -> Interpretation:
    return Interpretation(
        summary="Observed age summary.",
        findings=[
            Finding(claim="Mean age is 2.0 across 3 observations.", result_ids=["r1"]),
        ],
    )


def test_builds_independent_input_using_processed_version(state):
    original = deepcopy(state)

    request = build_interpretation_input(state)
    request.plan.assumptions.append("New assumption")
    request.analysis_results[0].values["columns"]["age"]["mean"] = 99.0

    assert request.run_id == "run1"
    assert request.dataset_version == "processed-v1"
    assert state == original


def test_returns_typed_success_without_changing_shared_state(state, draft):
    original = deepcopy(state)
    model = Mock(return_value=draft)

    response = interpretation_node(state, model)

    assert isinstance(response, AgentResponse)
    assert response.status == "success"
    assert response.updates.interpretation == draft
    assert model.call_count == 1
    assert state == original


@pytest.mark.parametrize("field", ["plan", "processed_dataset"])
def test_missing_required_output_does_not_fall_back_or_call_model(state, field):
    state[field] = None
    state["interpretation"] = Interpretation(summary="Old draft")
    original = deepcopy(state)
    model = Mock()

    response = interpretation_node(state, model)

    model.assert_not_called()
    assert response.error.code == "INVALID_DATA"
    assert response.error.retryable is False
    assert response.updates.model_dump(exclude_unset=True) == {"interpretation": None}
    assert state == original


@pytest.mark.parametrize("problem", ["missing_key", "empty_query", "invalid_dataset"])
def test_invalid_state_returns_safe_error(state, problem):
    if problem == "missing_key":
        del state["analysis_results"]
    elif problem == "empty_query":
        state["user_query"] = ""
    else:
        state["processed_dataset"].version = ""
    model = Mock()

    response = interpretation_node(state, model)

    model.assert_not_called()
    assert response.error.code == "INVALID_DATA"
    assert "unused.csv" not in response.model_dump_json()


@pytest.mark.parametrize("failure", ["stale", "empty", "timeout", "bad_output"])
def test_agent_failure_explicitly_clears_stale_draft_in_update(state, draft, failure):
    state["interpretation"] = Interpretation(summary="Old draft")
    model = Mock(return_value=draft)
    if failure == "stale":
        state["analysis_results"][0].dataset_version = "old-version"
    elif failure == "empty":
        state["analysis_results"] = []
    elif failure == "timeout":
        model.side_effect = TimeoutError("private details")
    else:
        model.return_value = Interpretation(summary=" ")
    original = deepcopy(state)

    response = interpretation_node(state, model)

    assert response.status == "error"
    assert response.error.retryable is (failure == "timeout")
    assert response.updates.model_dump(exclude_unset=True) == {"interpretation": None}
    assert state == original


def test_passes_targeted_revision_context_without_incrementing_limits(state, draft):
    state["interpretation"] = Interpretation(summary="Previous draft")
    state["critique"] = Critique(
        decision="revise",
        issues=[
            CritiqueIssue(
                code="CLAIM",
                severity="error",
                target_agent="interpretation",
                description="Mention the sample size",
            )
        ],
    )
    state["control"].revision_count = 1
    model = Mock(return_value=draft)

    response = interpretation_node(state, model)

    context = model.call_args.args[1]
    assert response.status == "success"
    assert context.previous_interpretation.summary == "Previous draft"
    assert context.revision_feedback == ["Mention the sample size"]
    assert state["control"].revision_count == 1


def test_does_not_read_unrelated_workflow_fields(state, draft):
    for key in (
        "dataset",
        "conversation_context",
        "control",
        "errors",
        "final_response",
        "clarification_question",
    ):
        del state[key]

    response = interpretation_node(state, Mock(return_value=draft))

    assert response.status == "success"


def test_unexpected_model_failure_is_left_to_harness(state):
    with pytest.raises(RuntimeError, match="unexpected"):
        interpretation_node(state, Mock(side_effect=RuntimeError("unexpected")))
