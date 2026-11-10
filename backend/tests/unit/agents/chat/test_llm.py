"""The live Chat adapter returns validated replies and normalizes SDK failures."""

import json
from types import SimpleNamespace
from unittest.mock import Mock

import httpx2
import pytest
from openai import APIConnectionError, APITimeoutError
from pydantic import ValidationError

from backend.app.agents.chat.llm import ChatLLM
from backend.app.agents.chat.schema import ChatContext

CONTEXT = ChatContext(message="Why drop rows?", user_query="Describe age")
REPLY = {"action": "answer", "text": "Missing ages were removed."}


@pytest.fixture
def completion(monkeypatch) -> Mock:
    for name, value in {
        "NTNU_LLM_MODEL": "test-model",
        "NTNU_LLM_API_KEY": "test-key",
        "NTNU_LLM_BASE_URL": "https://provider.invalid/v1",
    }.items():
        monkeypatch.setenv(name, value)
    create = Mock()
    monkeypatch.setattr(
        "backend.app.agents.chat.llm.OpenAI",
        lambda **kwargs: SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=create)),
            close=Mock(),
        ),
    )
    return create


def _respond(completion: Mock, content: str, finish_reason: str = "stop") -> None:
    completion.return_value = SimpleNamespace(
        choices=[
            SimpleNamespace(
                finish_reason=finish_reason,
                message=SimpleNamespace(
                    content=content, refusal=None, tool_calls=None, function_call=None
                ),
            )
        ]
    )


def test_reply_is_parsed_from_json_with_schema_and_context(completion):
    _respond(completion, json.dumps(REPLY))

    reply = ChatLLM()("Answer follow-ups.", CONTEXT)

    system, user = completion.call_args.kwargs["messages"]
    assert reply.text == "Missing ages were removed."
    assert system["content"].startswith("Answer follow-ups.")
    assert "analysis_request" in system["content"]
    assert json.loads(user["content"])["message"] == "Why drop rows?"
    assert completion.call_args.kwargs["response_format"] == {"type": "json_object"}


@pytest.mark.parametrize("count", [0, 2])
def test_invalid_choice_count_is_rejected_as_a_failed_reply(completion, count):
    _respond(completion, json.dumps(REPLY))
    completion.return_value.choices *= count

    with pytest.raises(ValueError, match="exactly one Chat response"):
        ChatLLM()("Answer.", CONTEXT)

    completion.assert_called_once()


@pytest.mark.parametrize(
    "field,value",
    [
        ("refusal", "Declined"),
        ("tool_calls", ["unexpected"]),
        ("function_call", "unexpected"),
    ],
)
def test_refusal_and_unexpected_tool_calls_are_rejected(completion, field, value):
    _respond(completion, json.dumps(REPLY))
    setattr(completion.return_value.choices[0].message, field, value)

    with pytest.raises(ValueError, match="not a refusal or tool call"):
        ChatLLM()("Answer.", CONTEXT)

    completion.assert_called_once()


def test_fenced_json_is_accepted(completion):
    _respond(completion, f"```json\n{json.dumps(REPLY)}\n```")

    assert ChatLLM()("Answer.", CONTEXT).action == "answer"


@pytest.mark.parametrize(
    "content,finish_reason,error",
    [
        (json.dumps(REPLY), "length", ValueError),
        ("", "stop", ValueError),
        ('{"action": "new_analysis", "text": "Soon"}', "stop", ValidationError),
    ],
)
def test_incomplete_or_invalid_output_is_rejected(
    completion, content, finish_reason, error
):
    _respond(completion, content, finish_reason)

    with pytest.raises(error):
        ChatLLM()("Answer.", CONTEXT)


@pytest.mark.parametrize(
    "failure,expected",
    [("timeout", TimeoutError), ("connection", ConnectionError)],
)
def test_provider_failures_are_normalized_without_details(
    completion, failure, expected
):
    request = httpx2.Request("POST", "https://provider.invalid/v1/chat/completions")
    completion.side_effect = (
        APITimeoutError(request=request)
        if failure == "timeout"
        else APIConnectionError(request=request, message="private details")
    )

    with pytest.raises(expected) as raised:
        ChatLLM()("Answer.", CONTEXT)

    assert "private" not in str(raised.value)
