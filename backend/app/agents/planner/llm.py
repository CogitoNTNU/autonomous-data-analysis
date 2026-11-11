"""LLM integration for the Planner Agent."""

from __future__ import annotations

import json
import os
from typing import Any

from openai import (
    APIConnectionError,
    APIResponseValidationError,
    APIStatusError,
    APITimeoutError,
    OpenAI,
)
from pydantic import ValidationError

from backend.app.agents.planner.agent import PlannerContext
from backend.app.agents.planner.context import context_message
from backend.app.agents.planner.schema import PlannerOutput
from backend.app.contracts.models import PlanStep
from backend.app.tools.registry import ToolRegistry, registered_tool, validate_call
from backend.app.core.llm_config import load_llm_settings
from backend.app.core.llm_errors import raise_model_timeout, raise_provider_error
from backend.app.core.llm_transport import model_timeout
from backend.app.core.exceptions import ModelConnectionError, ModelOutputError

MAX_TOOL_ROUNDS = 5
MAX_TOOL_CALLS = 20


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
            timeout=model_timeout(self.settings.timeout_seconds),
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

        tool_calls_used = 0
        for round_number in range(MAX_TOOL_ROUNDS + 1):
            finalizing = (
                round_number == MAX_TOOL_ROUNDS or tool_calls_used == MAX_TOOL_CALLS
            )
            if finalizing:
                messages.append(
                    {
                        "role": "system",
                        "content": (
                            "The read-only inspection budget is complete. Return a complete "
                            "PlannerOutput now using the evidence already supplied. No further "
                            "inspection calls are allowed. Request clarification if the "
                            "available evidence is insufficient."
                        ),
                    }
                )
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=tools,
                    response_format=_response_format(context.available_tools),
                    **({"tool_choice": "none"} if finalizing else {}),
                    **self.settings.completion.request_kwargs(),
                )
            except APITimeoutError as error:
                raise_model_timeout(error, "Planner")
            except APIConnectionError as error:
                raise ModelConnectionError(
                    "The Planner provider is unreachable."
                ) from error
            except APIStatusError as error:
                raise_provider_error(error, "Planner")
            except APIResponseValidationError as error:
                raise ModelOutputError("invalid_envelope") from error

            choices = getattr(response, "choices", None)
            if not isinstance(choices, list) or len(choices) != 1:
                raise ModelOutputError("invalid_envelope")
            choice = choices[0]
            message = getattr(choice, "message", None)
            if message is None:
                raise ModelOutputError("invalid_envelope")
            if getattr(message, "refusal", None):
                raise ValueError("The Planner declined to provide a plan.")
            if choice.finish_reason == "length":
                raise ModelOutputError("incomplete_response")
            expected_reason = "tool_calls" if message.tool_calls else "stop"
            if choice.finish_reason != expected_reason:
                if choice.finish_reason not in {"content_filter", "function_call"}:
                    raise ModelOutputError("invalid_envelope")
                raise ValueError("The Planner response did not finish normally.")

            if not message.tool_calls:
                if message.content is None:
                    raise ModelOutputError("empty_response")

                return self._parse_output(message.content)

            if finalizing:
                raise ValueError("Planner exceeded maximum number of tool rounds")

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
                tool_calls_used += 1
                if tool_calls_used > MAX_TOOL_CALLS:
                    raise ValueError("Planner exceeded its inspection-call budget")
                tool_name = tool_call.function.name
                tool = registered_tool(self.inspection_registry, tool_name)

                if tool is None:
                    raise ValueError(f"Unknown inspection tool: {tool_name}")
                if tool.phase != "inspection":
                    raise ValueError("Planner may only execute inspection tools")

                arguments = json.loads(tool_call.function.arguments)

                validated_arguments = tool.input_model.model_validate(arguments)
                step = PlanStep(
                    step_id=tool_call.id, tool_name=tool.name, arguments=arguments
                )
                problem = validate_call(step, context.dataset, tool)
                if problem is not None:
                    raise ValueError("Planner inspection arguments failed validation")

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

        raise ValueError("Planner exceeded maximum number of tool rounds")

    @staticmethod
    def _parse_output(content: str) -> PlannerOutput:
        if not isinstance(content, str):
            raise ModelOutputError("invalid_envelope")
        content = content.strip()
        if not content:
            raise ModelOutputError("empty_response")

        if content.startswith("```") and content.endswith("```"):
            lines = content.splitlines()

            if lines[0].strip().lower() in {"```", "```json"}:
                content = "\n".join(lines[1:-1]).strip()

        try:
            return PlannerOutput.model_validate_json(content, strict=True)
        except ValidationError as error:
            raise ModelOutputError(
                "invalid_json",
                validation_types=sorted({item["type"] for item in error.errors()}),
            ) from error

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


def _response_format(available_tools: list[dict[str, Any]]) -> dict[str, Any]:
    """Constrain the output branch while retaining registered tool arguments."""
    schema = PlannerOutput.model_json_schema()
    executable_names = [
        tool["name"]
        for tool in available_tools
        if tool.get("phase") in {"preprocessing", "analysis"}
    ]
    if executable_names:
        schema["$defs"]["PlanStep"]["properties"]["tool_name"]["enum"] = (
            executable_names
        )
    schema["required"] = ["plan", "clarification"]
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "planner_output",
            "strict": False,
            "schema": schema,
        },
    }
