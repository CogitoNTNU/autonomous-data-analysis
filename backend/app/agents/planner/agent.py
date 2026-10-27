"""Core orchestration for the Planner Agent."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.app.agents.planner.schema import PlannerOutput
from backend.app.agents.planner.validation import validate_plan
from backend.app.contracts.errors import AgentError
from backend.app.contracts.models import (
    ConversationMessage,
    Critique,
    DatasetReference,
    Plan,
    PlannerUpdates,
    PlanStep,
)
from backend.app.contracts.responses import AgentResponse
from backend.app.tools.registry import ToolRegistry, canonical_tool_name

SOURCE = "planner"
PROMPT_PATH = Path(__file__).with_name("prompt.md")


@dataclass(frozen=True)
class PlannerContext:
    """Information available to the Planner model for one planning attempt."""

    user_query: str
    dataset: DatasetReference
    conversation_context: list[ConversationMessage]
    critique: Critique | None
    available_tools: list[dict[str, Any]]
    previous_plan: Plan | None = None


PlannerModel = Callable[
    [str, PlannerContext],
    PlannerOutput,
]


def run_planner(
    user_query: str,
    dataset: DatasetReference,
    conversation_context: list[ConversationMessage],
    critique: Critique | None,
    registry: ToolRegistry,
    model: PlannerModel,
    *,
    previous_plan: Plan | None = None,
) -> AgentResponse[PlannerUpdates]:
    """Create and validate a plan or return a clarification response."""

    context = PlannerContext(
        user_query=user_query,
        dataset=dataset,
        conversation_context=conversation_context,
        critique=critique,
        available_tools=registry.list_tools(),
        previous_plan=previous_plan,
    )

    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    output = model(prompt, context)

    if output.clarification is not None:
        return AgentResponse(
            status="needs_clarification",
            updates=PlannerUpdates(),
            clarification_question=output.clarification.question,
        )

    plan = output.plan
    if plan is None:
        return _invalid_output("Planner returned neither plan nor clarification")
    plan = _with_registered_tool_names(plan, registry)

    try:
        validate_plan(plan, dataset, registry)
    except ValueError as exc:
        return _invalid_output(str(exc))

    return AgentResponse(
        status="success",
        updates=PlannerUpdates(plan=plan),
    )


def _with_registered_tool_names(plan: Plan, registry: ToolRegistry) -> Plan:
    return plan.model_copy(
        update={
            "preprocessing_steps": [
                _named(step, registry) for step in plan.preprocessing_steps
            ],
            "analysis_steps": [_named(step, registry) for step in plan.analysis_steps],
        }
    )


def _named(step: PlanStep, registry: ToolRegistry) -> PlanStep:
    name = canonical_tool_name(registry, step.tool_name)
    if name == step.tool_name:
        return step
    return step.model_copy(update={"tool_name": name})


def _invalid_output(message: str) -> AgentResponse[PlannerUpdates]:
    return AgentResponse(
        status="error",
        updates=PlannerUpdates(),
        error=AgentError(
            code="INVALID_OUTPUT",
            message=message,
            source=SOURCE,
        ),
    )
