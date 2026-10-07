"""Settings are explicit, validated, and safe to inspect."""

import pytest

from backend.app.core.llm_config import IDUN_BASE_URL, IDUN_MODEL, load_llm_settings


def test_uses_documented_idun_defaults_and_masks_key():
    settings = load_llm_settings({"NTNU_LLM_API_KEY": "test-private-key"})

    assert str(settings.base_url) == IDUN_BASE_URL
    assert settings.model_name == IDUN_MODEL
    assert settings.timeout_seconds == 120
    assert settings.api_key.get_secret_value() == "test-private-key"
    assert "test-private-key" not in repr(settings)
    assert "test-private-key" not in settings.model_dump_json()


def test_explicit_configuration_is_preserved():
    settings = load_llm_settings(
        {
            "NTNU_LLM_API_KEY": "test-key",
            "NTNU_LLM_BASE_URL": "https://custom.invalid/v1",
            "NTNU_LLM_MODEL": "chosen-model",
            "NTNU_LLM_TIMEOUT_SECONDS": "45",
        }
    )

    assert str(settings.base_url) == "https://custom.invalid/v1"
    assert settings.model_name == "chosen-model"
    assert settings.timeout_seconds == 45


@pytest.mark.parametrize("key", [None, "", "   "])
def test_requires_nonempty_key(key):
    environment = {} if key is None else {"NTNU_LLM_API_KEY": key}

    with pytest.raises(ValueError, match="NTNU_LLM_API_KEY"):
        load_llm_settings(environment)


@pytest.mark.parametrize(
    "name,value",
    [
        ("NTNU_LLM_BASE_URL", ""),
        ("NTNU_LLM_BASE_URL", "http://example.invalid/v1"),
        ("NTNU_LLM_BASE_URL", "https://user:password@example.invalid/v1"),
        ("NTNU_LLM_BASE_URL", "https://example.invalid/v1?key=secret"),
        ("NTNU_LLM_BASE_URL", "https://example.invalid/v1#fragment"),
        ("NTNU_LLM_MODEL", " "),
        ("NTNU_LLM_TIMEOUT_SECONDS", "0"),
        ("NTNU_LLM_TIMEOUT_SECONDS", "-1"),
        ("NTNU_LLM_TIMEOUT_SECONDS", "nan"),
        ("NTNU_LLM_TIMEOUT_SECONDS", "inf"),
        ("NTNU_LLM_TIMEOUT_SECONDS", "invalid"),
    ],
)
def test_rejects_invalid_settings_without_exposing_values(name, value):
    with pytest.raises(ValueError) as error:
        load_llm_settings({"NTNU_LLM_API_KEY": "private-key", name: value})

    assert "private-key" not in str(error.value)
    assert "password" not in str(error.value)
    assert "key=secret" not in str(error.value)
