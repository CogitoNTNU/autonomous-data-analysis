"""All live adapters expose the same safe provider HTTP failure categories."""

from types import SimpleNamespace
from unittest.mock import Mock

import httpx2
import pytest
from openai import APIStatusError

from backend.app.agents.chat.llm import ChatLLM
from backend.app.agents.chat.schema import ChatContext
from backend.app.agents.critic.llm import CriticLLM
from backend.app.agents.critic.schema import CriticContext
from backend.app.agents.planner.agent import PlannerContext
from backend.app.agents.planner.llm import PlannerLLM
from backend.app.contracts.models import DatasetReference, Interpretation
from backend.app.core.exceptions import ModelProviderError
from backend.app.tools.registry import ToolRegistry


@pytest.fixture(params=["planner", "critic", "chat"])
def adapter(request, monkeypatch):
    source = request.param
    for name, value in {
        "NTNU_LLM_MODEL": "test-model",
        "NTNU_LLM_API_KEY": "test-key",
        "NTNU_LLM_BASE_URL": "https://provider.invalid/v1",
    }.items():
        monkeypatch.setenv(name, value)
    completion = Mock()
    monkeypatch.setattr(
        f"backend.app.agents.{source}.llm.OpenAI",
        lambda **kwargs: SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=completion)),
        ),
    )
    if source == "planner":
        model = PlannerLLM(ToolRegistry())
        context = PlannerContext(
            "Describe age",
            DatasetReference(
                dataset_id="d", version="v1", storage_ref="a.csv", schema={}
            ),
            [],
            None,
            [],
        )
    elif source == "critic":
        model = CriticLLM()
        context = CriticContext(
            user_query="Describe age",
            plan=None,
            analysis_results=[],
            interpretation=Interpretation(summary="Age was described."),
        )
    else:
        model = ChatLLM()
        context = ChatContext(message="Why?", user_query="Describe age")
    return model, context, completion


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
        (429, "insufficient_quota", ModelProviderError),
        (429, "billing_hard_limit_reached", ModelProviderError),
    ],
)
def test_http_failures_are_safe_and_classified_for_harness(
    adapter, status, code, expected
):
    model, context, completion = adapter
    request = httpx2.Request("POST", "https://provider.invalid/v1/chat/completions")
    completion.side_effect = APIStatusError(
        "private provider details",
        response=httpx2.Response(status, request=request),
        body={"code": code},
    )

    with pytest.raises(expected) as raised:
        model("Use the recorded evidence.", context)

    assert "private" not in str(raised.value)
    completion.assert_called_once()
