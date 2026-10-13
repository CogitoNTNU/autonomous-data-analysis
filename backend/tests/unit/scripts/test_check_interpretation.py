"""Connection-check commands never use a real key or network in tests."""

from unittest.mock import MagicMock, Mock

import pytest
from openai import OpenAIError

from backend.app.contracts.models import Finding, Interpretation
from backend.scripts import check_interpretation as check


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch):
    for name in (
        "NTNU_LLM_API_KEY",
        "NTNU_LLM_BASE_URL",
        "NTNU_LLM_MODEL",
        "NTNU_LLM_TIMEOUT_SECONDS",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def provider(monkeypatch):
    monkeypatch.setenv("NTNU_LLM_API_KEY", "test-private-key")
    client = MagicMock()
    monkeypatch.setattr(check, "OpenAI", client)
    model = Mock(
        return_value=Interpretation(
            summary="Synthetic summary",
            findings=[
                Finding(
                    claim="The reported mean is 20.0 across 3 observations.",
                    result_ids=["sample-result"],
                ),
            ],
        )
    )
    monkeypatch.setattr(check, "InterpretationLLM", Mock(return_value=model))
    return client, model


def test_missing_key_returns_configuration_error_without_constructing_client(
    monkeypatch, capsys
):
    client = Mock(side_effect=AssertionError("Must not contact provider"))
    monkeypatch.setattr(check, "OpenAI", client)

    assert check.main([]) == 2
    assert "NTNU_LLM_API_KEY" in capsys.readouterr().err
    client.assert_not_called()


def test_config_only_does_not_contact_provider(provider, capsys):
    client, model = provider

    assert check.main(["--check-config"]) == 0
    client.assert_not_called()
    model.assert_not_called()
    output = capsys.readouterr().out
    assert "not been tested" in output
    assert "test-private-key" not in output


def test_one_synthetic_request_uses_idun_settings(provider, capsys):
    client, model = provider

    assert check.main([]) == 0
    assert model.call_count == 1
    assert client.call_args.kwargs["base_url"] == "https://llm.hpc.ntnu.no/v1"
    assert client.call_args.kwargs["max_retries"] == 0
    context = model.call_args.args[1]
    assert context.evidence.results[0].values["columns"]["value"]["mean"] == 20.0
    assert context.assumptions == ["These are synthetic test values."]
    output = capsys.readouterr().out
    assert "passed" in output
    assert "test-private-key" not in output
    assert "Synthetic summary" not in output


@pytest.mark.parametrize(
    "error", [TimeoutError("private diagnostic"), ValueError("private diagnostic")]
)
def test_agent_failure_reports_safe_outcome(provider, capsys, error):
    provider[1].side_effect = error

    assert check.main([]) == 1
    output = capsys.readouterr().err
    assert "failed" in output
    assert "private diagnostic" not in output
    assert "test-private-key" not in output


def test_provider_failure_reports_safe_message(provider, capsys):
    provider[0].side_effect = OpenAIError("private provider details")

    assert check.main([]) == 1
    assert "private provider details" not in capsys.readouterr().err
