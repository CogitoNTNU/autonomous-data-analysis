"""LLM integration for the Planner Agent."""

from __future__ import annotations

import json
import os
from typing import Any

from openai import (
    APIConnectionError,
    APIResponseValidationError,
    APITimeoutError,
    OpenAI,
)

from backend.app.agents.planner.agent import PlannerContext
from backend.app.agents.planner.context import context_message
from backend.app.agents.planner.schema import PlannerOutput
from backend.app.tools.registry import ToolRegistry, registered_tool
from backend.app.core.llm_config import load_llm_settings

MAX_TOOL_ROUNDS = 5


class PlannerLLM:
    def __init__(
        self,
        inspection_registry: ToolRegistry,
    ) -> None:
        self.inspection_registry = inspection_registry
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
        context: PlannerContext,
    ) -> PlannerOutput:
        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    f"{prompt}\n\n"
                    "Your final response must be valid JSON matching this schema:\n"
                    f"{json.dumps(PlannerOutput.model_json_schema(), indent=2)}"
                ),
            },
            {
                "role": "user",
                "content": context_message(context, self.inspection_registry),
            },
        ]

        tools = self._inspection_tools()

        for _ in range(MAX_TOOL_ROUNDS):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=tools,
                    **self.settings.completion.request_kwargs(),
                )
            except APITimeoutError as error:
                raise TimeoutError("The Planner model timed out.") from error
            except APIConnectionError as error:
                raise ConnectionError("The Planner provider is unreachable.") from error
            except APIResponseValidationError as error:
                raise ValueError(
                    "The Planner provider returned an invalid response."
                ) from error

            choice = response.choices[0]
            if choice.finish_reason in {"length", "content_filter"}:
                raise ValueError("The Planner response did not finish normally.")
            message = choice.message

            if not message.tool_calls:
                if message.content is None:
                    raise ValueError("Planner returned no output")

                return self._parse_output(message.content)

            messages.append(
                {
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [
                        tool_call.model_dump() for tool_call in message.tool_calls
                    ],
                }
            )

            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool = registered_tool(self.inspection_registry, tool_name)

                if tool is None:
                    raise ValueError(f"Unknown inspection tool: {tool_name}")

                arguments = json.loads(tool_call.function.arguments)

                validated_arguments = tool.input_model.model_validate(arguments)

                result = tool.run(
                    context.dataset,
                    **validated_arguments.model_dump(),
                )

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(
                            result,
                            default=str,
                        ),
                    }
                )

        raise RuntimeError("Planner exceeded maximum number of tool rounds")

    @staticmethod
    def _parse_output(content: str) -> PlannerOutput:
        content = content.strip()

        if content.startswith("```") and content.endswith("```"):
            lines = content.splitlines()

            if lines[0].strip().lower() in {"```", "```json"}:
                content = "\n".join(lines[1:-1]).strip()

        return PlannerOutput.model_validate_json(content)

    def _inspection_tools(
        self,
    ) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["schema"],
                },
            }
            for tool in self.inspection_registry.list_tools()
        ]

    def close(self) -> None:
        self.client.close()
