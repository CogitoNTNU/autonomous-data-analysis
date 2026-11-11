"""OpenAI-compatible Chat Completions adapter using structured output."""

from typing import Any

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
from backend.app.core.llm_config import CompletionOptions, IDUN_TIMEOUT_SECONDS
from backend.app.core.llm_errors import raise_model_timeout, raise_provider_error
from backend.app.core.llm_transport import model_timeout
from backend.app.core.exceptions import ModelConnectionError

from .context import serialize_context
from .schema import InterpretationContext

DEFAULT_TIMEOUT_SECONDS = IDUN_TIMEOUT_SECONDS


class InterpretationLLM:
    """One request using an injected client, endpoint, credentials, and model.

    The caller owns the client's lifetime. SDK retries are disabled on a copy;
    timeout_seconds is an HTTP operation timeout, not a workflow deadline.
    Strict JSON Schema output is requested with no capability fallback or tools.
    """

    def __init__(
        self,
        client: OpenAI,
        model_name: str,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        completion: CompletionOptions | None = None,
    ) -> None:
        if not model_name.strip():
            raise ValueError("A model name is required")
        self._client = client.with_options(
            max_retries=0, timeout=model_timeout(timeout_seconds)
        )
        self._model_name = model_name
        self._completion = completion or CompletionOptions()

    def __call__(
        self,
        prompt: str,
        context: InterpretationContext,
    ) -> Interpretation:
        """Return validated JSON or raise a provider-independent failure."""
        if not prompt.strip():
            raise ValueError("An interpretation prompt is required")
        content = serialize_context(context)
        try:
            completion = self._client.chat.completions.create(
                model=self._model_name,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": content},
                ],
                response_format=_response_format(context),
                **self._completion.request_kwargs(),
            )
        except APITimeoutError as error:
            raise_model_timeout(error, "interpretation")
        except APIConnectionError as error:
            raise ModelConnectionError(
                "The interpretation provider is unreachable"
            ) from error
        except APIStatusError as error:
            raise_provider_error(error, "interpretation")
        except APIResponseValidationError as error:
            raise ValueError("The provider returned an invalid response") from error
        return _parse_completion(completion)

    def close(self) -> None:
        self._client.close()

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


def _response_format(context: InterpretationContext) -> dict[str, Any]:
    """Return a strict schema limited to citations available in this context."""
    schema = Interpretation.model_json_schema()
    result_ids = [result.result_id for result in context.evidence.results]
    if result_ids:
        references = schema["$defs"]["Finding"]["properties"]["result_ids"]
        references["items"] = {"type": "string", "enum": result_ids}
    else:
        schema["properties"]["findings"]["maxItems"] = 0
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "interpretation",
            "strict": True,
            "schema": schema,
        },
    }
