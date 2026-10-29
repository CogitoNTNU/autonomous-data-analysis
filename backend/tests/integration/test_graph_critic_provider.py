"""Real SDK exception types are normalized before reaching graph error handling."""

import json
from types import SimpleNamespace
from unittest.mock import Mock

import httpx2
import pytest
from openai import APIConnectionError, APIResponseValidationError, APITimeoutError

from backend.app.agents.critic.llm import CriticLLM
from backend.app.contracts.models import Critique, DatasetReference
from backend.app.contracts.state import create_initial_state
from backend.app.graph.builder import build_graph
from backend.app.tools.registry import ToolRegistry


@pytest.fixture
def critic_provider(monkeypatch: pytest.MonkeyPatch) -> tuple[CriticLLM, Mock]:
    for name, value in {
        "NTNU_LLM_MODEL": "test-model",
        "NTNU_LLM_API_KEY": "test-key",
        "NTNU_LLM_BASE_URL": "https://provider.invalid/v1",
    }.items():
        monkeypatch.setenv(name, value)
    completion = Mock(
        return_value=SimpleNamespace(
            choices=[
                SimpleNamespace(
                    finish_reason="stop",
                    message=SimpleNamespace(
                        content=Critique(decision="approved").model_dump_json()
                    ),
                )
            ]
        )
    )
    monkeypatch.setattr(
        "backend.app.agents.critic.llm.OpenAI",
        lambda **kwargs: SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=completion))
        ),
    )
    return CriticLLM(), completion


@pytest.mark.parametrize(
    "failure,code,retryable",
    [
        ("timeout", "TIMEOUT", True),
        ("connection", "TOOL_FAILURE", True),
        ("sdk_validation", "INVALID_OUTPUT", False),
        ("invalid_json", "INVALID_OUTPUT", False),
        ("none", None, False),
    ],
)
def test_graph_classifies_critic_provider_failures(
    pipeline_dataset: DatasetReference,
    pipeline_registry: ToolRegistry,
    pipeline_models: tuple[Mock, Mock, Mock],
    critic_provider: tuple[CriticLLM, Mock],
    failure: str,
    code: str | None,
    retryable: bool,
) -> None:
    model, completion = critic_provider
    request = httpx2.Request("POST", "https://provider.invalid/v1/chat/completions")
    if failure == "timeout":
        completion.side_effect = APITimeoutError(request=request)
    elif failure == "connection":
        completion.side_effect = APIConnectionError(
            request=request, message="private details"
        )
    elif failure == "sdk_validation":
        completion.side_effect = APIResponseValidationError(
            response=httpx2.Response(200, request=request), body={"private": "details"}
        )
    elif failure == "invalid_json":
        completion.return_value.choices[0].message.content = "invalid JSON"
    planner, interpretation, _ = pipeline_models
    graph = build_graph(
        registry=pipeline_registry,
        planner_model=planner,
        interpretation_model=interpretation,
        critic_model=model,
    )
    state = create_initial_state(
        "Describe age", pipeline_dataset, max_revisions=2, max_retries=0
    )

    result = graph.invoke(state, config={"recursion_limit": 10})

    completion.assert_called_once()
    interpretation.assert_called_once()
    assert result["control"].revision_count == 0
    if code is None:
        assert result["control"].status == "completed"
        assert result["critique"].decision == "approved"
        assert result["errors"] == []
    else:
        assert result["control"].status == "error"
        assert result["critique"] is None
        assert len(result["errors"]) == 1
        error = result["errors"][0]
        assert error.source == "critic"
        assert error.code == code
        assert error.retryable is retryable
        assert "private" not in error.message


def test_critic_provider_receives_independent_execution_evidence(
    pipeline_dataset, pipeline_registry, pipeline_models, critic_provider
):
    model, completion = critic_provider
    graph = build_graph(
        pipeline_registry,
        pipeline_models[0],
        interpretation_model=pipeline_models[1],
        critic_model=model,
    )
    state = create_initial_state("Describe age", pipeline_dataset)

    result = graph.invoke(state, config={"recursion_limit": 15})

    payload = json.loads(completion.call_args.kwargs["messages"][1]["content"])
    assert result["control"].status == "completed"
    assert payload["preprocessing_report"]["rows_before"] == 3
    assert payload["preprocessing_report"]["rows_after"] == 2
    assert payload["analysis_execution_report"]["completed_step_ids"] == [
        "describe-age"
    ]
    assert payload["analysis_execution_report"]["outcome"] == "complete"
    assert "warnings" in payload
