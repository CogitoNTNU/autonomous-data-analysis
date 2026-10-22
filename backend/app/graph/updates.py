"""Build common state updates from a single typed agent response."""

from typing import TypedDict, TypeVar

from backend.app.contracts.errors import AgentError
from backend.app.contracts.models import (
    AgentName,
    ContractModel,
    RunControl,
    WarningEvent,
)
from backend.app.contracts.responses import AgentResponse, ResponseStatus
from backend.app.contracts.state import AgentState

UpdatesT = TypeVar("UpdatesT", bound=ContractModel)


class OutcomeUpdates(TypedDict):
    last_node_status: ResponseStatus
    control: RunControl
    clarification_question: str | None
    warnings: list[WarningEvent]
    errors: list[AgentError]


def outcome_updates(
    state: AgentState,
    response: AgentResponse[UpdatesT],
    *,
    agent: AgentName,
) -> OutcomeUpdates:
    """Return independent replacement values for common workflow fields.

    Responses contain only the current attempt's warnings/error. These lists
    include previous history, so graph fields must not also use append reducers.
    Agent-owned payloads, routing, retries, and final completion are handled by
    the graph adapters. A successful intermediate attempt leaves the run active.
    """
    control = RunControl.model_validate(
        {
            **state["control"].model_dump(),
            "current_agent": agent,
            "status": "running" if response.status == "success" else response.status,
        }
    )
    errors = list(state["errors"])
    if response.error is not None:
        errors.append(response.error)
    return OutcomeUpdates(
        last_node_status=response.status,
        control=control,
        clarification_question=response.clarification_question,
        warnings=[
            warning.model_copy(deep=True)
            for warning in [*state["warnings"], *response.warnings]
        ],
        errors=[error.model_copy(deep=True) for error in errors],
    )
