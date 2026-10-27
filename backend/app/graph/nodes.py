"""Run bounded agents and translate their typed responses into graph updates."""

import logging
from copy import deepcopy

from backend.app.agents.analysis.node import analysis_node
from backend.app.agents.critic.agent import CriticModel
from backend.app.agents.critic.node import critic_node
from backend.app.agents.interpretation.node import interpretation_node
from backend.app.agents.interpretation.schema import InterpretationModel
from backend.app.agents.planner.agent import PlannerModel
from backend.app.agents.planner.node import planner_node
from backend.app.agents.preprocessing.workflow import preprocessing_node
from backend.app.contracts.errors import AgentError, ErrorCode
from backend.app.contracts.models import (
    AgentName,
    CriticUpdates,
    Critique,
    InterpretationUpdates,
    PreprocessingUpdates,
)
from backend.app.contracts.responses import AgentResponse
from backend.app.contracts.state import AgentState
from backend.app.tools.registry import ToolRegistry

from .responses import AgentStateUpdate, translate_agent_response
from .routes import critique_error


def planner_graph_node(
    state: AgentState, registry: ToolRegistry, model: PlannerModel
) -> AgentStateUpdate:
    return translate_agent_response(state, planner_node(state, registry, model))


def preprocessing_graph_node(state: AgentState) -> AgentStateUpdate:
    try:
        response = preprocessing_node(state)
    except (ValueError, OSError) as error:
        response = AgentResponse[PreprocessingUpdates](
            status="error",
            updates=PreprocessingUpdates(),
            error=AgentError(
                code="INVALID_DATA"
                if isinstance(error, ValueError)
                else "TOOL_FAILURE",
                message="Preprocessing input is invalid."
                if isinstance(error, ValueError)
                else "Preprocessing could not access dataset storage.",
                source="preprocessing",
            ),
        )
    return translate_agent_response(state, response)


def analysis_graph_node(state: AgentState, registry: ToolRegistry) -> AgentStateUpdate:
    return translate_agent_response(state, analysis_node(state, registry=registry))


def interpretation_graph_node(
    state: AgentState, model: InterpretationModel
) -> AgentStateUpdate:
    # The agent reads the previous draft and critique before translation clears them.
    try:
        response = interpretation_node(state, model=model)
    except Exception as error:
        response = AgentResponse[InterpretationUpdates](
            status="error",
            updates=InterpretationUpdates(interpretation=None),
            error=_execution_error(error, "interpretation"),
        )
    updates = translate_agent_response(state, response)
    critique = state["critique"]
    if (
        state["control"].current_agent == "critic"
        and critique is not None
        and critique.decision == "revise"
    ):
        updates["control"] = updates["control"].model_copy(
            update={"revision_count": state["control"].revision_count + 1}
        )
    return updates


def critic_graph_node(state: AgentState, model: CriticModel) -> AgentStateUpdate:
    """Evaluate one draft, recording unsupported or exhausted revisions explicitly."""
    try:
        # Critic models receive mutable context; protect authoritative evidence.
        response = critic_node(deepcopy(state), model=model)
        if response.error is not None:
            response = AgentResponse[CriticUpdates](
                status="error",
                updates=CriticUpdates(),
                warnings=response.warnings,
                error=response.error.model_copy(
                    update={"message": "Critic evaluation failed."}
                ),
            )
        elif response.updates.critique is not None:
            critique = Critique.model_validate(response.updates.critique.model_dump())
            diagnostic = critique_error(critique, state["control"])
            response = AgentResponse[CriticUpdates](
                status="error" if diagnostic is not None else "success",
                updates=CriticUpdates(critique=critique),
                warnings=response.warnings,
                error=diagnostic,
            )
    except Exception as error:
        response = AgentResponse[CriticUpdates](
            status="error",
            updates=CriticUpdates(),
            error=_execution_error(error, "critic"),
        )
    updates = translate_agent_response(state, response)
    critique = updates["critique"]
    errors = updates.get("errors", state["errors"])
    logging.getLogger(__name__).info(
        "critic.reviewed",
        extra={
            "run_id": state["run_id"],
            "node": "critic",
            "critic_decision": critique.decision if critique is not None else None,
            "revision_count": state["control"].revision_count,
            "error_category": errors[-1].code if errors else None,
        },
    )
    return updates


def _execution_error(error: Exception, source: AgentName) -> AgentError:
    """Expose a safe diagnostic without leaking exception messages or retrying."""
    code: ErrorCode = "TOOL_FAILURE"
    if isinstance(error, TimeoutError):
        code = "TIMEOUT"
    elif isinstance(error, ValueError):
        code = "INVALID_OUTPUT"
    return AgentError(
        code=code,
        message=f"The {source} attempt failed.",
        source=source,
        retryable=isinstance(error, (TimeoutError, ConnectionError)),
    )
