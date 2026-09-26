"""Build Planner context, including evidence needed for cleaning plans."""

import json
from typing import Any

from backend.app.agents.planner.agent import PlannerContext
from backend.app.tools.registry import ToolRegistry

CLEANING_TERMS = ("clean", "deduplic", "normaliz", "standardiz")
PREVIEW_LIMIT = 20


def context_message(context: PlannerContext, registry: ToolRegistry) -> str:
    """Serialize planning context and inspect rows for explicit cleaning tasks."""
    data: dict[str, Any] = {
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
    preview = _cleaning_preview(context, registry)
    if preview is not None:
        data["dataset_preview"] = preview
    return json.dumps(data, default=str)


def _cleaning_preview(
    context: PlannerContext, registry: ToolRegistry
) -> dict[str, Any] | None:
    query = context.user_query.casefold()
    if not any(term in query for term in CLEANING_TERMS):
        return None
    tool = registry.get("preview_data")
    if tool is None:
        return None
    arguments = tool.input_model.model_validate(
        {"columns": None, "limit": PREVIEW_LIMIT}
    )
    return tool.run(context.dataset, **arguments.model_dump())
