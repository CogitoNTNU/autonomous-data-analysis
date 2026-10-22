from langgraph.graph import END, START, StateGraph
from functools import partial

from backend.app.graph.lifecycle import finish_run, start_run

from backend.app.graph.nodes import (
    planner_graph_node,
    analysis_graph_node,
    preprocessing_graph_node,
    interpretation_graph_node,
)

from backend.app.contracts.state import AgentState
from backend.app.agents.planner.agent import PlannerModel
from backend.app.agents.interpretation.schema import InterpretationModel
from backend.app.tools.registry import ToolRegistry

from backend.app.graph.routes import (
    route_after_planner,
    route_after_preprocessing,
    route_after_analysis,
)


def build_graph(
    registry: ToolRegistry,
    planner_model: PlannerModel,
    interpretation_model: InterpretationModel,
):
    
    builder = StateGraph(AgentState)
    
    # Add nodes
    builder.add_node(
        "planner",
        partial(
            planner_graph_node,
            registry=registry,
            model=planner_model,
        )
    )
    builder.add_node(
        "preprocessing",
        preprocessing_graph_node
    )
    builder.add_node(
        "analysis",
        partial(
            analysis_graph_node,
            registry=registry,  
        )
    )

    builder.add_node("start_run", start_run)
    builder.add_node("finish_run", finish_run)
    builder.add_edge(START, "start_run")
    builder.add_edge("start_run", "planner")

    builder.add_conditional_edges(
        "planner",
        route_after_planner, 
        {
            "preprocessing": "preprocessing",
            "end": "finish_run",
        },
    )

    builder.add_conditional_edges(
        "preprocessing",
        route_after_preprocessing,
        {
            "analysis": "analysis",
            "end": "finish_run",
        },
    )

    builder.add_node(
        "interpretation",
        partial(
            interpretation_graph_node,
            model=interpretation_model
        )
    )

    builder.add_conditional_edges(
        "analysis",
        route_after_analysis,
        {
            "interpretation": "interpretation",
            "end": "finish_run",
        }
    )

    builder.add_edge("interpretation", "finish_run")
    builder.add_edge("finish_run", END)

    return builder.compile()