"""The Critic requests constrained JSON and rejects incomplete provider output."""

import json

import httpx2
import pytest
from openai import OpenAI

from backend.app.agents.critic.llm import CriticLLM
from backend.app.agents.critic.schema import CriticContext
from backend.app.contracts.models import Interpretation
from backend.app.core.exceptions import ModelOutputError


@pytest.fixture
def provider(monkeypatch):
    monkeypatch.setenv("NTNU_LLM_API_KEY", "test-key")
    monkeypatch.setenv("NTNU_LLM_BASE_URL", "https://provider.invalid/v1")
    body = {
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
                    "content": '{"decision":"approved"}',
                },
            }
        ],
    }
    sent = []

    def handler(request):
        sent.append(json.loads(request.content))
        return httpx2.Response(200, json=body)

    def factory(**kwargs):
        return OpenAI(
            **kwargs, http_client=httpx2.Client(transport=httpx2.MockTransport(handler))
        )

    monkeypatch.setattr("backend.app.agents.critic.llm.OpenAI", factory)
    model = CriticLLM()
    context = CriticContext(
        user_query="Describe age",
        plan=None,
        analysis_results=[],
        interpretation=Interpretation(summary="Recorded evidence"),
    )
    yield model, context, body, sent
    model.close()


def test_requests_constrained_schema_and_returns_valid_review(provider):
    model, context, _, sent = provider

    result = model("Review the evidence.", context)

    assert result.decision == "approved"
    schema = sent[0]["response_format"]
    assert schema["type"] == "json_schema"
    assert schema["json_schema"]["name"] == "critique"
    assert schema["json_schema"]["strict"] is True
    assert schema["json_schema"]["schema"]["$defs"]["CritiqueIssue"]["properties"][
        "target_agent"
    ]["enum"] == [
        "planner",
        "preprocessing",
        "analysis",
        "interpretation",
    ]
    assert len(sent) == 1


@pytest.mark.parametrize(
    "content",
    [
        "",
        "  ",
        "not JSON",
        '```json\n{"decision":"approved"}\n```',
        '{"decision":"approve"}',
        '{"decision":"approved","private-secret":1}',
    ],
)
def test_rejects_invalid_content_with_safe_diagnostics(provider, content):
    model, context, body, sent = provider
    body["choices"][0]["message"]["content"] = content

    with pytest.raises(ModelOutputError) as raised:
        model("Review the evidence.", context)

    assert raised.value.reason in {"empty_response", "invalid_json"}
    assert "private-secret" not in str(raised.value)
    assert len(sent) == 1


@pytest.mark.parametrize(
    "change,reason",
    [
        ("length", "incomplete_response"),
        ("empty_choices", "invalid_envelope"),
        ("missing_message", "invalid_envelope"),
    ],
)
def test_rejects_incomplete_response_envelopes(provider, change, reason):
    model, context, body, _ = provider
    if change == "length":
        body["choices"][0]["finish_reason"] = "length"
    elif change == "empty_choices":
        body["choices"] = []
    else:
        del body["choices"][0]["message"]

    with pytest.raises(ModelOutputError) as raised:
        model("Review the evidence.", context)

    assert raised.value.reason == reason


@pytest.mark.parametrize("kind", ["refusal", "content_filter", "tool_calls"])
def test_non_review_response_is_explicit_and_is_not_a_format_repair(provider, kind):
    model, context, body, _ = provider
    if kind == "refusal":
        body["choices"][0]["message"]["refusal"] = "Cannot review"
    else:
        body["choices"][0]["finish_reason"] = kind

    with pytest.raises(ValueError) as raised:
        model("Review the evidence.", context)

    assert not isinstance(raised.value, ModelOutputError)
