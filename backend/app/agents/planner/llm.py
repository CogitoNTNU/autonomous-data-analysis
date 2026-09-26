"""LLM integration for the Planner Agent."""

from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI

from backend.app.agents.planner.agent import PlannerContext
from backend.app.agents.planner.schema import PlannerOutput
from backend.app.tools.registry import ToolRegistry

MAX_TOOL_ROUNDS = 5


class PlannerLLM:
    def __init__(
        self,
        inspection_registry: ToolRegistry,
    ) -> None:
        self.inspection_registry = inspection_registry
        self.model = os.environ["NTNU_LLM_MODEL"]
        self.client = OpenAI(
            base_url=os.environ["NTNU_LLM_BASE_URL"],
            api_key=os.environ["NTNU_LLM_API_KEY"],
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
                "content": self._context_message(context),
            },
        ]

        tools = self._inspection_tools()

        for _ in range(MAX_TOOL_ROUNDS):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
            )

            message = response.choices[0].message

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
                tool = self.inspection_registry.get(tool_name)

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

    @staticmethod
    def _context_message(
        context: PlannerContext,
    ) -> str:
        data = {
            "user_query": context.user_query,
            "dataset": context.dataset.model_dump(by_alias=True),
            "conversation_context": [
                message.model_dump() for message in context.conversation_context
            ],
            "critique": (
                context.critique.model_dump() if context.critique is not None else None
            ),
            "available_tools": context.available_tools,
        }

        return json.dumps(
            data,
            default=str,
        )
