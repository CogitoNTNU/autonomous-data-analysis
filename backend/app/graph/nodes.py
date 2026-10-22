# PLANNER
from backend.app.agents.planner.agent import PlannerModel
from backend.app.agents.planner.node import planner_node

#
from backend.app.agents.analysis.node import analysis_node
from backend.app.agents.preprocessing.workflow import preprocessing_node

from backend.app.agents.interpretation.node import interpretation_node
from backend.app.agents.interpretation.schema import InterpretationModel

from backend.app.contracts.state import AgentState
from backend.app.graph.responses import (
    AgentStateUpdate,
    translate_agent_response,
)
from backend.app.tools.registry import ToolRegistry


def planner_graph_node(
        state: AgentState,
        registry: ToolRegistry,
        model: PlannerModel
) -> AgentStateUpdate:
    response = planner_node(
        state=state,
        registry=registry,
        model=model
    )

    return translate_agent_response(state, response)


def preprocessing_graph_node(state: AgentState) -> AgentStateUpdate:
    response = preprocessing_node(state)
    return translate_agent_response(state, response)


def analysis_graph_node(
        state: AgentState,
        registry: ToolRegistry,
) -> AgentStateUpdate:
    response = analysis_node(
        state=state,
        registry=registry
    )

    return translate_agent_response(state, response)


def interpretation_graph_node(
        state: AgentState,
        model: InterpretationModel,
) -> AgentStateUpdate:
    response = interpretation_node(
        state=state,
        model=model,
    )

    return translate_agent_response(state, response)