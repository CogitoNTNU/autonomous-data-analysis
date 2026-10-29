"""All live agent adapters receive the same validated request policy."""

import json

import httpx2
import pytest
from openai import OpenAI

from backend.app.agents.critic.llm import CriticLLM
from backend.app.agents.planner.llm import PlannerLLM
from backend.app.agents.interpretation.schema import (
    InterpretationContext,
    InterpretationEvidence,
)
from backend.app.services.interpretation_request import live_interpretation_model
from backend.app.tools.registry import ToolRegistry


@pytest.fixture
def environment(monkeypatch):
    for key, value in {
        "NTNU_LLM_API_KEY": "test-key",
        "NTNU_LLM_BASE_URL": "https://provider.invalid/v1",
        "NTNU_LLM_MODEL": "Inferact/GLM-5.3-NVFP4",
        "NTNU_LLM_TIMEOUT_SECONDS": "75",
        "NTNU_LLM_MAX_TOKENS": "2048",
        "NTNU_LLM_REASONING_EFFORT": "low",
    }.items():
        monkeypatch.setenv(key, value)


@pytest.mark.parametrize("agent", ["planner", "critic"])
def test_planner_and_critic_use_the_shared_timeout_and_generation_policy(
    monkeypatch, environment, agent
):
    from unittest.mock import Mock

    factory = Mock()
    monkeypatch.setattr(f"backend.app.agents.{agent}.llm.OpenAI", factory)
    model = PlannerLLM(ToolRegistry()) if agent == "planner" else CriticLLM()

    assert factory.call_args.kwargs["timeout"] == 75
    assert factory.call_args.kwargs["max_retries"] == 0
    assert model.settings.completion.request_kwargs() == {
        "max_tokens": 2048,
        "reasoning_effort": "low",
    }


def test_live_interpretation_uses_configured_timeout_instead_of_30_seconds(
    monkeypatch, environment
):
    sent = []

    def handler(request):
        sent.append(request)
        return httpx2.Response(
            200,
            json={
                "id": "c1",
                "object": "chat.completion",
                "created": 0,
                "model": "test",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": '{"summary":"No evidence available."}',
                        },
                    }
                ],
            },
        )

    client = OpenAI(
        api_key="test-key",
        base_url="https://provider.invalid/v1",
        http_client=httpx2.Client(transport=httpx2.MockTransport(handler)),
    )
    monkeypatch.setattr(
        "backend.app.services.interpretation_request.ntnu_client", lambda: client
    )
    model = live_interpretation_model()
    try:
        model(
            "Interpret.",
            InterpretationContext(
                user_query="Describe age",
                objective="Describe age",
                assumptions=[],
                expected_outputs=[],
                evidence=InterpretationEvidence(),
                artifacts=[],
            ),
        )
        assert sent[0].extensions["timeout"]["read"] == 75
        assert json.loads(sent[0].content)["reasoning_effort"] == "low"
        assert len(sent) == 1
    finally:
        model.close()


@pytest.mark.parametrize("agent", ["planner", "critic"])
@pytest.mark.parametrize("finish_reason", ["stop", "length"])
def test_generation_limits_reach_planner_and_critic_http_requests(
    monkeypatch, environment, agent, finish_reason
):
    from backend.app.agents.planner.agent import PlannerContext
    from backend.app.agents.critic.schema import CriticContext
    from backend.app.contracts.models import DatasetReference, Interpretation

    sent = []
    output = (
        {"plan": {"plan_id": "p1", "objective": "Describe age"}}
        if agent == "planner"
        else {"decision": "approved"}
    )

    def handler(request):
        sent.append(request)
        return httpx2.Response(
            200,
            json={
                "id": "c1",
                "object": "chat.completion",
                "created": 0,
                "model": "test",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": finish_reason,
                        "message": {"role": "assistant", "content": json.dumps(output)},
                    }
                ],
            },
        )

    def factory(**kwargs):
        return OpenAI(
            **kwargs, http_client=httpx2.Client(transport=httpx2.MockTransport(handler))
        )

    monkeypatch.setattr(f"backend.app.agents.{agent}.llm.OpenAI", factory)
    if agent == "planner":
        model = PlannerLLM(ToolRegistry())
        context = PlannerContext(
            "Describe age",
            DatasetReference(
                dataset_id="d", version="v1", storage_ref="unused", schema={}
            ),
            [],
            None,
            [],
        )
    else:
        model = CriticLLM()
        context = CriticContext(
            user_query="Describe age",
            plan=None,
            analysis_results=[],
            interpretation=Interpretation(summary="No evidence"),
        )
    try:
        if finish_reason == "length":
            with pytest.raises(ValueError, match="did not finish"):
                model("Review the supplied context.", context)
        else:
            model("Review the supplied context.", context)
        assert sent[0].extensions["timeout"]["read"] == 75
        assert json.loads(sent[0].content)["reasoning_effort"] == "low"
        assert json.loads(sent[0].content)["max_tokens"] == 2048
        assert len(sent) == 1
    finally:
        model.close()
