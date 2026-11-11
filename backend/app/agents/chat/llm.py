"""LLM integration for follow-up messages to the Chat agent."""

import json
import os

from openai import (
    APIConnectionError,
    APIResponseValidationError,
    APIStatusError,
    APITimeoutError,
    OpenAI,
)

from backend.app.contracts.dialogue import ChatReply
from backend.app.core.llm_config import load_llm_settings
from backend.app.core.llm_errors import raise_model_timeout, raise_provider_error
from backend.app.core.llm_transport import model_timeout
from backend.app.core.exceptions import ModelConnectionError

from .context import serialize_context
from .schema import ChatContext


class ChatLLM:
    def __init__(self) -> None:
        self.settings = load_llm_settings(os.environ)
        self.model = self.settings.model_name
        self.client = OpenAI(
            base_url=str(self.settings.base_url),
            api_key=self.settings.api_key.get_secret_value(),
            max_retries=0,
            timeout=model_timeout(self.settings.timeout_seconds),
        )

    def __call__(self, prompt: str, context: ChatContext) -> ChatReply:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"{prompt}\n\n"
                            "Return JSON matching this schema:\n"
                            f"{json.dumps(ChatReply.model_json_schema())}"
                        ),
                    },
                    {"role": "user", "content": serialize_context(context)},
                ],
                response_format={"type": "json_object"},
                **self.settings.completion.request_kwargs(),
            )
        except APITimeoutError as error:
            raise_model_timeout(error, "Chat")
        except APIConnectionError as error:
            raise ModelConnectionError("The Chat provider is unreachable.") from error
        except APIStatusError as error:
            raise_provider_error(error, "Chat")
        except APIResponseValidationError as error:
            raise ValueError(
                "The Chat provider returned an invalid response."
            ) from error

        if len(response.choices) != 1:
            raise ValueError("Expected exactly one Chat response.")
        choice = response.choices[0]
        if choice.finish_reason != "stop":
            raise ValueError("The Chat response did not finish normally.")
        message = choice.message
        if message.refusal or message.tool_calls or message.function_call:
            raise ValueError("Expected a Chat reply, not a refusal or tool call.")
        content = (message.content or "").strip()
        if not content:
            raise ValueError("Chat returned no output")
        if content.startswith("```"):
            content = "\n".join(content.splitlines()[1:-1]).strip()
        return ChatReply.model_validate_json(content)

    def close(self) -> None:
        self.client.close()
