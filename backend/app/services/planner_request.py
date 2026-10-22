"""Run the planner for one uploaded dataset and return a JSON payload."""

from backend.app.agents.planner.agent import PlannerModel
from backend.app.agents.planner.node import planner_node
from backend.app.contracts.models import ConversationMessage, DatasetReference
from backend.app.contracts.state import create_initial_state
from backend.app.tools.registry import ToolRegistry


def plan_question(
    dataset: DatasetReference,
    question: str,
    messages: list[ConversationMessage],
    registry: ToolRegistry,
    model: PlannerModel,
) -> dict[str, object]:
    if not question.strip():
        raise ValueError("The question is empty")
    state = create_initial_state(
        question,
        dataset,
        conversation_context=messages,
    )
    updates = planner_node(state, registry, model)
    return _payload(updates)


def _payload(updates: dict[str, object]) -> dict[str, object]:
    question = updates.get("clarification_question")
    if isinstance(question, str) and question:
        return {"status": "needs_clarification", "question": question}
    plan = updates.get("plan")
    if plan is not None and hasattr(plan, "model_dump"):
        return {"status": "success", "plan": plan.model_dump()}
    return {"status": "error", "message": _error_message(updates)}


def _error_message(updates: dict[str, object]) -> str:
    errors = updates.get("errors")
    if isinstance(errors, list) and errors:
        message = getattr(errors[0], "message", None)
        if isinstance(message, str) and message:
            return message
    return "The planner could not produce a plan"
