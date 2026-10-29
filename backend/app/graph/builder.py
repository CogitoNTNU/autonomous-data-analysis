"""Build the pipeline with targeted Critic revisions and per-operation retries."""

from functools import partial

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from backend.app.agents.critic.agent import CriticModel
from backend.app.agents.interpretation.schema import InterpretationModel
from backend.app.agents.planner.agent import PlannerModel
from backend.app.contracts.state import AgentState
from backend.app.tools.registry import ToolRegistry

from .interaction import chat_graph_node, clarify
from .lifecycle import finish_run, start_run
from .observability import measured_node
from .nodes import (
    analysis_graph_node,
    critic_graph_node,
    interpretation_graph_node,
    planner_graph_node,
    preprocessing_graph_node,
)
from .routes import (
    route_after_analysis,
    route_after_critic,
    route_after_interpretation,
    route_after_planner,
    route_after_preprocessing,
)


def build_graph(
    registry: ToolRegistry,
    planner_model: PlannerModel,
    *,
    interpretation_model: InterpretationModel,
    critic_model: CriticModel,
    checkpointer: BaseCheckpointSaver | None = None,
    conversational: bool = False,
) -> CompiledStateGraph:
    """Inject models; all revision and retry budgets come from the run's state."""
    if conversational and checkpointer is None:
        raise ValueError("Interactive workflows require a checkpointer")
    builder = StateGraph(AgentState)
    if conversational:
        builder.add_node("clarification", clarify)
        builder.add_conditional_edges(
            "clarification",
            lambda state: "finish_run" if state["last_node_error"] else "planner",
            {"finish_run": "finish_run", "planner": "planner"},
        )
        builder.add_node("chat", measured_node("chat", chat_graph_node))
        builder.add_edge("chat", "finish_run")

    builder.add_node("start_run", start_run)
    builder.add_node("finish_run", finish_run)
    builder.add_node(
        "planner",
        measured_node(
            "planner",
            partial(planner_graph_node, registry=registry, model=planner_model),
        ),
    )
    builder.add_node(
        "preprocessing", measured_node("preprocessing", preprocessing_graph_node)
    )
    builder.add_node(
        "analysis",
        measured_node("analysis", partial(analysis_graph_node, registry=registry)),
    )
    builder.add_node(
        "interpretation",
        measured_node(
            "interpretation",
            partial(interpretation_graph_node, model=interpretation_model),
        ),
    )
    builder.add_node(
        "critic",
        measured_node("critic", partial(critic_graph_node, model=critic_model)),
    )
    builder.add_edge(START, "start_run")
    builder.add_edge("start_run", "planner")
    builder.add_conditional_edges(
        "planner",
        _conversational_planner_route if conversational else route_after_planner,
        {
            "planner": "planner",
            "preprocessing": "preprocessing",
            "end": "finish_run",
            **({"clarification": "clarification"} if conversational else {}),
        },
    )
    builder.add_conditional_edges(
        "preprocessing",
        route_after_preprocessing,
        {"preprocessing": "preprocessing", "analysis": "analysis", "end": "finish_run"},
    )
    builder.add_conditional_edges(
        "analysis",
        route_after_analysis,
        {
            "analysis": "analysis",
            "interpretation": "interpretation",
            "end": "finish_run",
        },
    )
    builder.add_conditional_edges(
        "interpretation",
        route_after_interpretation,
        {"interpretation": "interpretation", "critic": "critic", "end": "finish_run"},
    )
    builder.add_conditional_edges(
        "critic",
        _conversational_critic_route if conversational else route_after_critic,
        {
            "planner": "planner",
            "preprocessing": "preprocessing",
            "analysis": "analysis",
            "interpretation": "interpretation",
            "critic": "critic",
            "end": "finish_run",
            **({"chat": "chat"} if conversational else {}),
        },
    )
    builder.add_edge("finish_run", END)
    return builder.compile(checkpointer=checkpointer)


def _conversational_planner_route(state: AgentState) -> str:
    if state["clarification_question"] is not None:
        return "clarification"
    return route_after_planner(state)


def _conversational_critic_route(state: AgentState) -> str:
    route = route_after_critic(state)
    critique = state["critique"]
    if (
        route == "end"
        and state["last_node_error"] is None
        and critique is not None
        and critique.decision == "approved"
    ):
        return "chat"
    return route
