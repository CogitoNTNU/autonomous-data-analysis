"""LLM integration for the Critic Agent."""

import json
import os

from openai import OpenAI

from backend.app.agents.critic.agent import CriticContext
from backend.app.contracts.models import Critique


class CriticLLM:
    def __init__(self) -> None:
        self.model = os.environ["NTNU_LLM_MODEL"]

        self.client = OpenAI(
            base_url=os.environ["NTNU_LLM_BASE_URL"],
            api_key=os.environ["NTNU_LLM_API_KEY"],
        )

    def __call__(
        self,
        prompt: str,
        context: CriticContext,
    ) -> Critique:
        payload = {
            "user_query": context.user_query,
            "plan": (
                context.plan.model_dump(mode="json")
                if context.plan is not None
                else None
            ),
            "analysis_results": [
                result.model_dump(mode="json") for result in context.analysis_results
            ],
            "interpretation": context.interpretation.model_dump(mode="json"),
        }

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
                    "content": json.dumps(payload),
                },
            ],
        )

        content = response.choices[0].message.content

        if not content:
            raise ValueError("Critic returned no output")

        content = content.strip()

        if content.startswith("```"):
            content = "\n".join(content.splitlines()[1:-1]).strip()

        return Critique.model_validate_json(content)
