"""OpenAI-compatible Chat Completions adapter; requires JSON-object mode."""

import json
from math import isfinite
from typing import NoReturn

from openai import (
    APIConnectionError,
    APIResponseValidationError,
    APIStatusError,
    APITimeoutError,
    OpenAI,
)
from openai.types.chat import ChatCompletion
from pydantic import ValidationError

from backend.app.contracts.models import Interpretation
from backend.app.core.exceptions import ModelProviderError

from .context import serialize_context
from .schema import InterpretationContext

DEFAULT_TIMEOUT_SECONDS = 30.0


class InterpretationLLM:
    """One request using an injected client, endpoint, credentials, and model.

    The caller owns the client's lifetime. SDK retries are disabled on a copy;
    timeout_seconds is an HTTP operation timeout, not a workflow deadline.
    JSON mode is requested explicitly with no capability fallback or tools.
    """

    def __init__(
        self,
        client: OpenAI,
        model_name: str,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        if not model_name.strip():
            raise ValueError("A model name is required")
        if not isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("Model timeout must be finite and positive")
        self._client = client.with_options(max_retries=0, timeout=timeout_seconds)
        self._model_name = model_name

    def __call__(
        self,
        prompt: str,
        context: InterpretationContext,
    ) -> Interpretation:
        """Return validated JSON or raise a provider-independent failure."""
        if not prompt.strip():
            raise ValueError("An interpretation prompt is required")
        content = serialize_context(context)
        schema = json.dumps(Interpretation.model_json_schema())
        try:
            completion = self._client.chat.completions.create(
                model=self._model_name,
                messages=[
                    {
                        "role": "system",
                        "content": f"{prompt}\n\nReturn JSON matching this schema:\n{schema}",
                    },
                    {"role": "user", "content": content},
                ],
                response_format={"type": "json_object"},
            )
        except APITimeoutError as error:
            raise TimeoutError("The interpretation model timed out") from error
        except APIConnectionError as error:
            raise ConnectionError(
                "The interpretation provider is unreachable"
            ) from error
        except APIStatusError as error:
            _raise_status_error(error)
        except APIResponseValidationError as error:
            raise ValueError("The provider returned an invalid response") from error
        return _parse_completion(completion)

    @staticmethod
    def parse_output(content: str) -> Interpretation:
        """Reject empty, fenced, malformed, or schema-invalid JSON output."""
        if not content.strip():
            raise ValueError("The interpretation model returned no content")
        try:
            return Interpretation.model_validate_json(content, strict=True)
        except ValidationError as error:
            raise ValueError(
                "The interpretation model returned invalid JSON"
            ) from error


def _parse_completion(completion: ChatCompletion) -> Interpretation:
    # The SDK's default parsing may accept incomplete response envelopes.
    completion = ChatCompletion.model_validate(completion.model_dump())
    if len(completion.choices) != 1:
        raise ValueError("Expected exactly one interpretation response")
    choice = completion.choices[0]
    message = choice.message
    if choice.finish_reason != "stop":
        raise ValueError("The interpretation response did not finish normally")
    if message.refusal or message.tool_calls or message.function_call:
        raise ValueError("Expected an interpretation, not a refusal or tool call")
    if message.content is None:
        raise ValueError("The interpretation model returned no content")
    return InterpretationLLM.parse_output(message.content)


def _raise_status_error(error: APIStatusError) -> NoReturn:
    if error.status_code == 408:
        raise TimeoutError("The interpretation provider timed out") from error
    if error.code in {"insufficient_quota", "billing_hard_limit_reached"}:
        raise ModelProviderError(
            "The model request exceeded the provider quota"
        ) from error
    if error.status_code in {409, 429} or 500 <= error.status_code < 600:
        raise ConnectionError(
            "The interpretation provider is temporarily unavailable"
        ) from error
    raise ModelProviderError(
        "The interpretation provider rejected the request"
    ) from error
