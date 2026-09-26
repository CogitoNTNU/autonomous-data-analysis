"""State adapter for the Planner Agent."""

from backend.app.agents.planner.agent import PlannerModel, run_planner
from backend.app.contracts.state import AgentState
from backend.app.tools.registry import ToolRegistry


def planner_node(
    state: AgentState,
    registry: ToolRegistry,
    model: PlannerModel,
) -> dict[str, object]:
    """Run the Planner Agent and convert its response into state updates."""

    response = run_planner(
        user_query=state["user_query"],
        dataset=state["dataset"],
        conversation_context=state["conversation_context"],
        critique=state["critique"],
        registry=registry,
        model=model,
    )

    state_updates: dict[str, object] = {
        "warnings": [*state["warnings"], *response.warnings],
        "clarification_question": response.clarification_question,
    }

    if response.status == "success":
        state_updates["plan"] = response.updates.plan

    if response.status == "error" and response.error is not None:
        state_updates["errors"] = [*state["errors"], response.error]

    return state_updates
