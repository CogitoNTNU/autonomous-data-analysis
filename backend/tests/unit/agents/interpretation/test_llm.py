"""Exercise the real SDK against an in-memory HTTP transport, never a provider."""

import json

import httpx2
import pytest
from openai import OpenAI

from backend.app.agents.interpretation.llm import InterpretationLLM
from backend.app.agents.interpretation.schema import (
    InterpretationContext,
    InterpretationEvidence,
)
from backend.app.contracts.models import Interpretation
from backend.app.core.exceptions import ModelProviderError


@pytest.fixture
def context() -> InterpretationContext:
    return InterpretationContext(
        user_query="Describe age",
        objective="Summarize age",
        assumptions=[],
        expected_outputs=[],
        evidence=InterpretationEvidence(),
        artifacts=[],
    )


@pytest.fixture
def completion() -> dict:
    draft = Interpretation(
        summary="No usable evidence is available.",
        limitations=["Analysis is incomplete."],
    )
    return {
        "id": "test-completion",
        "object": "chat.completion",
        "created": 0,
        "model": "test-model",
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": draft.model_dump_json()},
            }
        ],
    }


@pytest.fixture
def client_factory():
    clients = []

    def create(handler):
        client = OpenAI(
            api_key="test-key",
            base_url="https://provider.invalid/v1",
            max_retries=2,
            http_client=httpx2.Client(transport=httpx2.MockTransport(handler)),
        )
        clients.append(client)
        return client

    yield create
    for client in clients:
        client.close()


def test_sends_one_json_request_with_schema_context_and_no_tools(
    client_factory, completion, context
):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx2.Response(200, json=completion)

    client = client_factory(handler)
    model = InterpretationLLM(client, "test-model", timeout_seconds=7)
    before = context.model_dump()

    result = model("Interpret supplied evidence.", context)

    assert result.summary == "No usable evidence is available."
    assert len(requests) == 1
    request = requests[0]
    payload = json.loads(request.content)
    assert request.url.path == "/v1/chat/completions"
    assert payload["model"] == "test-model"
    assert payload["response_format"] == {"type": "json_object"}
    assert "tools" not in payload
    assert payload["messages"][0]["role"] == "system"
    assert '"result_ids"' in payload["messages"][0]["content"]
    assert json.loads(payload["messages"][1]["content"]) == before
    assert request.extensions["timeout"]["read"] == 7
    assert context.model_dump() == before
    assert client.max_retries == 2


@pytest.mark.parametrize(
    "content",
    ["", " ", "not JSON", "{}", "```json\n{}\n```", '{"summary":"ok","extra":true}'],
)
def test_rejects_invalid_output_json(content):
    with pytest.raises(ValueError):
        InterpretationLLM.parse_output(content)


@pytest.mark.parametrize(
    "problem",
    [
        "empty_choices",
        "many_choices",
        "length",
        "content_filter",
        "tool_calls",
        "refusal",
        "no_content",
        "missing_model",
    ],
)
def test_rejects_unusable_completion_envelopes(
    client_factory, completion, context, problem
):
    choice = completion["choices"][0]
    if problem == "empty_choices":
        completion["choices"] = []
    elif problem == "many_choices":
        completion["choices"].append(choice.copy())
    elif problem in {"length", "content_filter"}:
        choice["finish_reason"] = problem
    elif problem == "tool_calls":
        choice["message"]["tool_calls"] = [
            {
                "id": "call-1",
                "type": "function",
                "function": {"name": "forbidden", "arguments": "{}"},
            }
        ]
    elif problem == "refusal":
        choice["message"]["refusal"] = "Refused"
    elif problem == "missing_model":
        del completion["model"]
    else:
        choice["message"]["content"] = None
    client = client_factory(lambda request: httpx2.Response(200, json=completion))

    with pytest.raises(ValueError):
        InterpretationLLM(client, "test-model")("Interpret.", context)


@pytest.mark.parametrize(
    "status,code,expected",
    [
        (408, None, TimeoutError),
        (409, None, ConnectionError),
        (429, "rate_limit_exceeded", ConnectionError),
        (500, None, ConnectionError),
        (503, None, ConnectionError),
        (400, None, ModelProviderError),
        (401, None, ModelProviderError),
        (403, None, ModelProviderError),
        (404, None, ModelProviderError),
        (422, None, ModelProviderError),
        (429, "insufficient_quota", ModelProviderError),
        (429, "billing_hard_limit_reached", ModelProviderError),
    ],
)
def test_maps_status_errors_without_retries_or_raw_error_text(
    client_factory, context, status, code, expected
):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx2.Response(
            status, json={"error": {"message": "private diagnostic", "code": code}}
        )

    model = InterpretationLLM(client_factory(handler), "test-model")

    with pytest.raises(expected) as caught:
        model("Interpret.", context)

    assert len(calls) == 1
    assert "private diagnostic" not in str(caught.value)
    assert caught.value.__cause__ is not None


@pytest.mark.parametrize(
    "transport_error,expected",
    [(httpx2.ReadTimeout, TimeoutError), (httpx2.ConnectError, ConnectionError)],
)
def test_maps_transport_errors_without_retries(
    client_factory, context, transport_error, expected
):
    calls = []

    def handler(request):
        calls.append(request)
        raise transport_error("private diagnostic", request=request)

    model = InterpretationLLM(client_factory(handler), "test-model")

    with pytest.raises(expected):
        model("Interpret.", context)

    assert len(calls) == 1


@pytest.mark.parametrize("timeout", [0, -1, float("inf"), float("nan")])
def test_rejects_invalid_timeout(client_factory, timeout):
    client = client_factory(lambda request: pytest.fail("Unexpected request"))

    with pytest.raises(ValueError, match="timeout"):
        InterpretationLLM(client, "test-model", timeout_seconds=timeout)


def test_rejects_empty_model_name(client_factory):
    client = client_factory(lambda request: pytest.fail("Unexpected request"))

    with pytest.raises(ValueError, match="model name"):
        InterpretationLLM(client, " ")


def test_rejects_empty_prompt_before_provider_call(client_factory, context):
    client = client_factory(lambda request: pytest.fail("Unexpected request"))

    with pytest.raises(ValueError, match="prompt"):
        InterpretationLLM(client, "test-model")(" ", context)
