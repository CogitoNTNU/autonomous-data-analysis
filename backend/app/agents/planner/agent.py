"""Core orchestration for the Planner Agent."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.app.agents.planner.validation import validate_plan
from backend.app.contracts.errors import AgentError
from backend.app.contracts.models import (
    ConversationMessage,
    Critique,
    DatasetReference,
    PlannerUpdates,
)
from backend.app.contracts.responses import AgentResponse
from backend.app.tools.registry import ToolRegistry

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


PlannerModel = Callable[
    [str, PlannerContext],
    AgentResponse[PlannerUpdates],
]


def run_planner(
    user_query: str,
    dataset: DatasetReference,
    conversation_context: list[ConversationMessage],
    critique: Critique | None,
    registry: ToolRegistry,
    model: PlannerModel,
) -> AgentResponse[PlannerUpdates]:
    """Create and validate a plan or return a clarification response."""
    context = PlannerContext(
        user_query=user_query,
        dataset=dataset,
        conversation_context=conversation_context,
        critique=critique,
        available_tools=registry.list_tools(),
    )
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    response = model(prompt, context)

    if response.status != "success":
        return response

    plan = response.updates.plan
    if plan is None:
        return _invalid_output("Planner returned success without a plan")

    try:
        validate_plan(plan, dataset, registry)
    except ValueError as exc:
        return _invalid_output(str(exc))

    return response


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
