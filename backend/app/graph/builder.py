from langgraph.graph import END, START, StateGraph
from functools import partial
from backend.app.agents.planner.node import planner_node
from backend.app.agents.preprocessing.workflow import preprocessing_node
from backend.app.agents.analysis.node import analysis_node
from backend.app.contracts.state import AgentState
from backend.app.agents.planner.agent import PlannerModel
from backend.app.tools.registry import ToolRegistry


def build_graph(registry: ToolRegistry, planner_model: PlannerModel):
    
    builder = StateGraph(AgentState)
    
    # Add nodes
    builder.add_node(
        "planner",
        partial(
            planner_node,
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
            analysis_node,
            registry=registry,  
        )
    )

    builder.add_edge(START, "planner")
    builder.add_edge("planner", END)

    return builder.compile()