"""Read explicit Idun client configuration without loading or logging secrets."""

from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, SecretStr, ValidationError

IDUN_BASE_URL = "https://llm.hpc.ntnu.no/v1"
IDUN_MODEL = "openai/gpt-oss-120b"
IDUN_TIMEOUT_SECONDS = 120.0


class LLMSettings(BaseModel):
    """Validated startup settings; api_key is masked in repr and JSON output."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    api_key: SecretStr = Field(min_length=1)
    base_url: HttpUrl
    model_name: str = Field(min_length=1)
    timeout_seconds: float = Field(gt=0, allow_inf_nan=False)


def load_llm_settings(environment: Mapping[str, str]) -> LLMSettings:
    """Read NTNU_LLM_* variables; use documented defaults only when absent.

    .env loading belongs to the launcher (uv run --env-file), not this module.
    The caller must supply the environment; importing this module performs no I/O.
    """
    key = environment.get("NTNU_LLM_API_KEY", "").strip()
    if not key:
        raise ValueError("Set NTNU_LLM_API_KEY in your local backend/.env file.")
    try:
        settings = LLMSettings(
            api_key=key,
            base_url=environment.get("NTNU_LLM_BASE_URL", IDUN_BASE_URL).strip(),
            model_name=environment.get("NTNU_LLM_MODEL", IDUN_MODEL).strip(),
            timeout_seconds=environment.get(
                "NTNU_LLM_TIMEOUT_SECONDS", str(IDUN_TIMEOUT_SECONDS)
            ),
        )
    except ValidationError as error:
        raise ValueError(
            "Invalid NTNU LLM configuration; check the URL, model, and timeout."
        ) from error
    url = settings.base_url
    if (
        url.scheme != "https"
        or url.username
        or url.password
        or url.query
        or url.fragment
    ):
        raise ValueError(
            "NTNU_LLM_BASE_URL must be HTTPS without credentials, query, or fragment."
        )
    return settings
