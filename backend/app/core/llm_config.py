"""Read explicit Idun client configuration without loading or logging secrets."""

from collections.abc import Mapping
from typing import Literal, Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, SecretStr, ValidationError

IDUN_BASE_URL = "https://llm.hpc.ntnu.no/v1"
IDUN_MODEL = "openai/gpt-oss-120b"
IDUN_TIMEOUT_SECONDS = 120.0


ReasoningEffort = Literal["low", "medium", "high", "max"]


class CompletionOptions(BaseModel):
    """Bound generated reasoning and answer tokens without truncating evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    max_tokens: int = Field(default=4096, ge=256, le=32768)
    reasoning_effort: ReasoningEffort | None = None

    def request_kwargs(self) -> dict[str, Any]:
        options: dict[str, Any] = {"max_tokens": self.max_tokens}
        if self.reasoning_effort is not None:
            options["reasoning_effort"] = self.reasoning_effort
        return options


class LLMSettings(BaseModel):
    """Validated startup settings; api_key is masked in repr and JSON output."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    api_key: SecretStr = Field(min_length=1)
    base_url: HttpUrl
    model_name: str = Field(min_length=1)
    timeout_seconds: float = Field(gt=0, allow_inf_nan=False)
    completion: CompletionOptions = Field(default_factory=CompletionOptions)


def load_llm_settings(environment: Mapping[str, str]) -> LLMSettings:
    """Read NTNU_LLM_* variables; use documented defaults only when absent.

    .env loading belongs to the launcher (uv run --env-file), not this module.
    The caller must supply the environment; importing this module performs no I/O.
    """
    key = environment.get("NTNU_LLM_API_KEY", "").strip()
    if not key:
        raise ValueError("Set NTNU_LLM_API_KEY in your local backend/.env file.")
    model_name = environment.get("NTNU_LLM_MODEL", IDUN_MODEL).strip()
    family = model_name.rsplit("/", 1)[-1].casefold()
    # These deployed model families support low effort; other providers opt in.
    default_effort = (
        "low"
        if family.startswith("glm-5.3") or family in {"gpt-oss-120b", "gpt-oss-20b"}
        else None
    )
    try:
        settings = LLMSettings(
            api_key=key,
            base_url=environment.get("NTNU_LLM_BASE_URL", IDUN_BASE_URL).strip(),
            model_name=model_name,
            timeout_seconds=environment.get(
                "NTNU_LLM_TIMEOUT_SECONDS", str(IDUN_TIMEOUT_SECONDS)
            ),
            completion=CompletionOptions(
                max_tokens=environment.get("NTNU_LLM_MAX_TOKENS", "4096"),
                reasoning_effort=environment.get(
                    "NTNU_LLM_REASONING_EFFORT", default_effort
                ),
            ),
        )
        if (
            family.startswith("glm-5.3")
            and settings.completion.reasoning_effort == "medium"
        ):
            raise ValueError("GLM-5.3 reasoning effort must be low, high, or max.")
    except ValidationError as error:
        raise ValueError(
            "Invalid NTNU LLM configuration; check the URL, model, timeout, and generation limits."
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
