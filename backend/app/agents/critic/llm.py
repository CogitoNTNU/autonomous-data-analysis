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

from .context import serialize_context


class CriticLLM:
    def __init__(self) -> None:
        self.model = os.environ["NTNU_LLM_MODEL"]

        self.client = OpenAI(
            base_url=os.environ["NTNU_LLM_BASE_URL"],
            api_key=os.environ["NTNU_LLM_API_KEY"],
            max_retries=0,
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
            )
        except APITimeoutError as error:
            raise TimeoutError("The Critic model timed out.") from error
        except APIConnectionError as error:
            raise ConnectionError("The Critic provider is unreachable.") from error
        except APIResponseValidationError as error:
            raise ValueError(
                "The Critic provider returned an invalid response."
            ) from error

        content = response.choices[0].message.content

        if not content:
            raise ValueError("Critic returned no output")

        content = content.strip()

        if content.startswith("```"):
            content = "\n".join(content.splitlines()[1:-1]).strip()

        return Critique.model_validate_json(content)
