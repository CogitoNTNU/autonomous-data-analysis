"""LLM integration for the Critic Agent."""

import json
import os

from openai import (
    APIConnectionError,
    APIResponseValidationError,
    APITimeoutError,
    OpenAI,
)

from backend.app.agents.critic.agent import CriticContext
from backend.app.contracts.models import Critique
from backend.app.core.llm_config import load_llm_settings

from .context import serialize_context


class CriticLLM:
    def __init__(self) -> None:
        self.settings = load_llm_settings(os.environ)
        self.model = self.settings.model_name

        self.client = OpenAI(
            base_url=str(self.settings.base_url),
            api_key=self.settings.api_key.get_secret_value(),
            max_retries=0,
            timeout=self.settings.timeout_seconds,
        )

    def __call__(
        self,
        prompt: str,
        context: CriticContext,
    ) -> Critique:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"{prompt}\n\n"
                            "Return JSON matching this schema:\n"
                            f"{json.dumps(Critique.model_json_schema())}"
                        ),
                    },
                    {
                        "role": "user",
                        "content": serialize_context(context),
                    },
                ],
                **self.settings.completion.request_kwargs(),
            )
        except APITimeoutError as error:
            raise TimeoutError("The Critic model timed out.") from error
        except APIConnectionError as error:
            raise ConnectionError("The Critic provider is unreachable.") from error
        except APIResponseValidationError as error:
            raise ValueError(
                "The Critic provider returned an invalid response."
            ) from error

        choice = response.choices[0]
        if choice.finish_reason != "stop":
            raise ValueError("The Critic response did not finish normally.")
        content = choice.message.content

        if not content:
            raise ValueError("Critic returned no output")

        content = content.strip()

        if content.startswith("```"):
            content = "\n".join(content.splitlines()[1:-1]).strip()

        return Critique.model_validate_json(content)

    def close(self) -> None:
        self.client.close()
