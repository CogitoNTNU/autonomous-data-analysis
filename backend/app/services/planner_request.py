"""Run the planner for one uploaded dataset and return a JSON payload."""

from backend.app.agents.planner.agent import PlannerModel
from backend.app.agents.planner.node import planner_node
from backend.app.contracts.models import (
    ConversationMessage,
    DatasetReference,
    PlannerUpdates,
)
from backend.app.contracts.responses import AgentResponse
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


def _payload(response: AgentResponse[PlannerUpdates]) -> dict[str, object]:
    if response.status == "needs_clarification":
        return {
            "status": "needs_clarification",
            "question": response.clarification_question,
        }
    plan = response.updates.plan
    if response.status == "success" and plan is not None:
        return {"status": "success", "plan": plan.model_dump()}
    message = response.error.message if response.error is not None else ""
    return {
        "status": "error",
        "message": message or "The planner could not produce a plan",
    }
