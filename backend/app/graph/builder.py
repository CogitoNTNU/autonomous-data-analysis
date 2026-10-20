from langgraph.graph import END, START, StateGraph
from functools import partial

# NEEDS TO BE CHANGED WITH THE TRANSLATOR
from backend.app.graph.nodes import planner_graph_node # DONE
from backend.app.graph.nodes import analysis_graph_node # DONE
from backend.app.agents.preprocessing.workflow import preprocessing_node

from backend.app.contracts.state import AgentState
from backend.app.agents.planner.agent import PlannerModel
from backend.app.tools.registry import ToolRegistry
from backend.app.graph.routes import route_after_planner


def build_graph(registry: ToolRegistry, planner_model: PlannerModel):
    
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
        preprocessing_node
    )
    builder.add_node(
        "analysis",
        partial(
            analysis_graph_node,
            registry=registry,  
        )
    )

    builder.add_edge(START, "planner")

    builder.add_conditional_edges(
        "planner",
        route_after_planner, 
        {
            "preprocessing": "preprocessing",
            "end": END,
        },
    )
    builder.add_edge("preprocessing", END)

    return builder.compile()