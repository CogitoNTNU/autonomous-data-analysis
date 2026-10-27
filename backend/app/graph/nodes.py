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
    AnalysisUpdates,
    CriticUpdates,
    Critique,
    InterpretationUpdates,
    PlannerUpdates,
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
    try:
        response = planner_node(deepcopy(state), registry, model)
    except (ValueError, OSError) as error:
        response = AgentResponse[PlannerUpdates](
            status="error",
            updates=PlannerUpdates(),
            error=_execution_error(error, "planner"),
        )
    return translate_agent_response(state, response)


def preprocessing_graph_node(state: AgentState) -> AgentStateUpdate:
    try:
        response = preprocessing_node(state)
    except (ValueError, OSError) as error:
        diagnostic = _execution_error(error, "preprocessing")
        if isinstance(error, ValueError):
            diagnostic = AgentError(
                code="INVALID_DATA",
                message="Preprocessing input is invalid.",
                source="preprocessing",
            )
        response = AgentResponse[PreprocessingUpdates](
            status="error",
            updates=PreprocessingUpdates(),
            error=diagnostic,
        )
    return translate_agent_response(state, response)


def analysis_graph_node(state: AgentState, registry: ToolRegistry) -> AgentStateUpdate:
    try:
        response = analysis_node(state, registry=registry)
    except (ValueError, OSError) as error:
        response = AgentResponse[AnalysisUpdates](
            status="error",
            updates=AnalysisUpdates(),
            error=_execution_error(error, "analysis"),
        )
    return translate_agent_response(state, response)


def interpretation_graph_node(
    state: AgentState, model: InterpretationModel
) -> AgentStateUpdate:
    # The agent reads the previous draft and critique before translation clears them.
    try:
        response = interpretation_node(state, model=model)
    except Exception as error:  # noqa: BLE001 - model boundary emits safe structured failures
        response = AgentResponse[InterpretationUpdates](
            status="error",
            updates=InterpretationUpdates(interpretation=None),
            error=_execution_error(error, "interpretation"),
        )
    return translate_agent_response(state, response)


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
    except Exception as error:  # noqa: BLE001 - model boundary emits safe structured failures
        response = AgentResponse[CriticUpdates](
            status="error",
            updates=CriticUpdates(),
            error=_execution_error(error, "critic"),
        )
    updates = translate_agent_response(state, response)
    critique = updates.get("critique")
    error = updates["last_node_error"]
    logging.getLogger(__name__).info(
        "critic.reviewed",
        extra={
            "run_id": state["run_id"],
            "node": "critic",
            "critic_decision": critique.decision if critique is not None else None,
            "revision_count": state["control"].revision_count,
            "error_category": error.code if error else None,
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
