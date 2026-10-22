"""State adapter for the Critic Agent."""

from backend.app.agents.critic.agent import (
    CriticModel,
    run_critic,
)
from backend.app.contracts.state import AgentState


def critic_node(
    state: AgentState,
    model: CriticModel,
) -> dict[str, object]:
    """Run the Critic and return state updates."""

    response = run_critic(
        user_query=state["user_query"],
        plan=state["plan"],
        analysis_results=state["analysis_results"],
        interpretation=state["interpretation"],
        model=model,
    )

    if response.status == "error":
        return {
            "errors": [*state["errors"], response.error],
        }

    return {
        "critique": response.updates.critique,
    }
