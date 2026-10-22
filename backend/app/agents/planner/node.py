"""State adapter for the Planner Agent."""

from backend.app.agents.planner.agent import PlannerModel, run_planner
from backend.app.contracts.state import AgentState
from backend.app.tools.registry import ToolRegistry
from backend.app.contracts.responses import AgentResponse
from backend.app.contracts.models import PlannerUpdates

def planner_node(
    state: AgentState,
    registry: ToolRegistry,
    model: PlannerModel,
) -> AgentResponse[PlannerUpdates]:
    """Run the Planner Agent and convert its response into a node for the harness"""

    return run_planner(
        user_query=state["user_query"],
        dataset=state["dataset"],
        conversation_context=state["conversation_context"],
        critique=state["critique"],
        registry=registry,
        model=model,
    )
