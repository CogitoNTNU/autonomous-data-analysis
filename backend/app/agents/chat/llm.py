"""LLM integration for follow-up messages to the Chat agent."""

import json
import os

from openai import (
    APIConnectionError,
    APIResponseValidationError,
    APITimeoutError,
    OpenAI,
)

from backend.app.contracts.dialogue import ChatReply
from backend.app.core.llm_config import load_llm_settings

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
            timeout=self.settings.timeout_seconds,
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
                **self.settings.completion.request_kwargs(),
            )
        except APITimeoutError as error:
            raise TimeoutError("The Chat model timed out.") from error
        except APIConnectionError as error:
            raise ConnectionError("The Chat provider is unreachable.") from error
        except APIResponseValidationError as error:
            raise ValueError(
                "The Chat provider returned an invalid response."
            ) from error

        choice = response.choices[0]
        if choice.finish_reason != "stop":
            raise ValueError("The Chat response did not finish normally.")
        content = (choice.message.content or "").strip()
        if not content:
            raise ValueError("Chat returned no output")
        if content.startswith("```"):
            content = "\n".join(content.splitlines()[1:-1]).strip()
        return ChatReply.model_validate_json(content)

    def close(self) -> None:
        self.client.close()
