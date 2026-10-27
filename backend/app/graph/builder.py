"""Build the analysis pipeline with bounded Critic feedback to Interpretation."""

from functools import partial

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from backend.app.agents.critic.agent import CriticModel
from backend.app.agents.interpretation.schema import InterpretationModel
from backend.app.agents.planner.agent import PlannerModel
from backend.app.contracts.state import AgentState
from backend.app.tools.registry import ToolRegistry

from .lifecycle import finish_run, start_run
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
) -> CompiledStateGraph:
    """Inject models and revise only Interpretation within the state's revision limit."""
    builder = StateGraph(AgentState)
    builder.add_node("start_run", start_run)
    builder.add_node("finish_run", finish_run)
    builder.add_node(
        "planner", partial(planner_graph_node, registry=registry, model=planner_model)
    )
    builder.add_node("preprocessing", preprocessing_graph_node)
    builder.add_node("analysis", partial(analysis_graph_node, registry=registry))
    builder.add_node(
        "interpretation", partial(interpretation_graph_node, model=interpretation_model)
    )
    builder.add_node("critic", partial(critic_graph_node, model=critic_model))
    builder.add_edge(START, "start_run")
    builder.add_edge("start_run", "planner")
    builder.add_conditional_edges(
        "planner",
        route_after_planner,
        {"preprocessing": "preprocessing", "end": "finish_run"},
    )
    builder.add_conditional_edges(
        "preprocessing",
        route_after_preprocessing,
        {"analysis": "analysis", "end": "finish_run"},
    )
    builder.add_conditional_edges(
        "analysis",
        route_after_analysis,
        {"interpretation": "interpretation", "end": "finish_run"},
    )
    builder.add_conditional_edges(
        "interpretation",
        route_after_interpretation,
        {"critic": "critic", "end": "finish_run"},
    )
    builder.add_conditional_edges(
        "critic",
        route_after_critic,
        {"interpretation": "interpretation", "end": "finish_run"},
    )
    builder.add_edge("finish_run", END)
    return builder.compile()
