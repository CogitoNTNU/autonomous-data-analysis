from functools import partial

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from backend.app.agents.interpretation.schema import InterpretationModel
from backend.app.agents.planner.agent import PlannerModel
from backend.app.contracts.state import AgentState
from backend.app.graph.nodes import (
    analysis_step,
    finish_draft,
    interpretation_step,
    planner_step,
    preprocessing_step,
)
from backend.app.graph.routes import (
    route_after_analysis,
    route_after_planner,
    route_after_preprocessing,
)
from backend.app.tools.registry import ToolRegistry


def build_graph(
    registry: ToolRegistry,
    planner_model: PlannerModel,
    interpretation_model: InterpretationModel,
) -> CompiledStateGraph:
    """Build a draft-producing pipeline; no Critic approval or retries yet."""

    builder = StateGraph(AgentState)

    # Add nodes
    builder.add_node(
        "planner",
        partial(
            planner_step,
            registry=registry,
            model=planner_model,
        ),
    )
    builder.add_node("preprocessing", preprocessing_step)
    builder.add_node(
        "analysis",
        partial(
            analysis_step,
            registry=registry,
        ),
    )

    builder.add_edge(START, "planner")

    builder.add_conditional_edges(
        "planner",
        route_after_planner,
        {
            "preprocessing": "preprocessing",
            "end": "finish_draft",
        },
    )
    builder.add_node(
        "interpretation", partial(interpretation_step, model=interpretation_model)
    )
    builder.add_node("finish_draft", finish_draft)
    builder.add_conditional_edges(
        "preprocessing",
        route_after_preprocessing,
        {"analysis": "analysis", "end": "finish_draft"},
    )
    builder.add_conditional_edges(
        "analysis",
        route_after_analysis,
        {"interpretation": "interpretation", "end": "finish_draft"},
    )
    builder.add_edge("interpretation", "finish_draft")
    builder.add_edge("finish_draft", END)

    return builder.compile()
