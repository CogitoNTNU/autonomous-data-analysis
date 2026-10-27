"""State adapter for the Critic Agent."""

from backend.app.agents.critic.agent import (
    CriticModel,
    run_critic,
)
from backend.app.contracts.models import CriticUpdates
from backend.app.contracts.responses import AgentResponse
from backend.app.contracts.state import AgentState


def critic_node(
    state: AgentState,
    model: CriticModel,
) -> AgentResponse[CriticUpdates]:
    """Return a typed review; the graph owns state translation and routing."""

    return run_critic(
        user_query=state["user_query"],
        plan=state["plan"],
        analysis_results=state["analysis_results"],
        interpretation=state["interpretation"],
        model=model,
    )
