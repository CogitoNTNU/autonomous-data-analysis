"""LLM integration for the Critic Agent."""

import json
import os

from openai import (
    APIConnectionError,
    APIResponseValidationError,
    APIStatusError,
    APITimeoutError,
    OpenAI,
)
from pydantic import ValidationError
from openai.types.chat import ChatCompletion

from backend.app.agents.critic.agent import CriticContext
from backend.app.contracts.models import Critique
from backend.app.core.llm_config import load_llm_settings
from backend.app.core.llm_errors import raise_model_timeout, raise_provider_error
from backend.app.core.llm_transport import model_timeout
from backend.app.core.exceptions import ModelConnectionError, ModelOutputError

from .context import serialize_context


class CriticLLM:
    def __init__(self) -> None:
        self.settings = load_llm_settings(os.environ)
        self.model = self.settings.model_name

        self.client = OpenAI(
            base_url=str(self.settings.base_url),
            api_key=self.settings.api_key.get_secret_value(),
            max_retries=0,
            timeout=model_timeout(self.settings.timeout_seconds),
        )

    def __call__(
        self,
        prompt: str,
        context: CriticContext,
    ) -> Critique:
        schema = Critique.model_json_schema()
        schema["$defs"]["CritiqueIssue"]["properties"]["target_agent"]["enum"] = [
            "planner",
            "preprocessing",
            "analysis",
            "interpretation",
        ]
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"{prompt}\n\n"
                            "Return JSON matching this schema:\n"
                            f"{json.dumps(schema)}"
                        ),
                    },
                    {
                        "role": "user",
                        "content": serialize_context(context),
                    },
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "critique",
                        "strict": True,
                        "schema": schema,
                    },
                },
                **self.settings.completion.request_kwargs(),
            )
        except APITimeoutError as error:
            raise_model_timeout(error, "Critic")
        except APIConnectionError as error:
            raise ModelConnectionError("The Critic provider is unreachable.") from error
        except APIStatusError as error:
            raise_provider_error(error, "Critic")
        except APIResponseValidationError as error:
            raise ModelOutputError("invalid_envelope") from error

        try:
            response = ChatCompletion.model_validate(response.model_dump())
        except (ValidationError, AttributeError) as error:
            raise ModelOutputError("invalid_envelope") from error
        if len(response.choices) != 1:
            raise ModelOutputError("invalid_envelope")
        choice = response.choices[0]
        if choice.finish_reason == "length":
            raise ModelOutputError("incomplete_response")
        if choice.finish_reason != "stop":
            raise ValueError("The Critic did not return a review.")
        if (
            choice.message.refusal
            or choice.message.tool_calls
            or choice.message.function_call
        ):
            raise ValueError("The Critic did not return a review.")
        content = choice.message.content

        if not content or not content.strip():
            raise ModelOutputError("empty_response")
        try:
            return Critique.model_validate_json(content, strict=True)
        except ValidationError as error:
            raise ModelOutputError(
                "invalid_json",
                validation_types=sorted({item["type"] for item in error.errors()}),
            ) from error

    def close(self) -> None:
        self.client.close()
