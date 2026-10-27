"""State adapter for the Planner Agent."""

from backend.app.agents.planner.agent import PlannerModel, run_planner
from backend.app.contracts.models import PlannerUpdates
from backend.app.contracts.responses import AgentResponse
from backend.app.contracts.state import AgentState
from backend.app.tools.registry import ToolRegistry


def planner_node(
    state: AgentState,
    registry: ToolRegistry,
    model: PlannerModel,
) -> AgentResponse[PlannerUpdates]:
    """Read workflow inputs and return the typed Planner response."""

    return run_planner(
        user_query=state["user_query"],
        dataset=state["dataset"],
        conversation_context=state["conversation_context"],
        critique=state["critique"],
        registry=registry,
        model=model,
        previous_plan=state["plan"],
    )
