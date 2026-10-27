"""Build common state updates from a single typed agent response."""

from typing import TypedDict, TypeVar

from backend.app.contracts.errors import AgentError
from backend.app.contracts.models import (
    AgentName,
    ContractModel,
    RevisionRecord,
    RunControl,
    WarningEvent,
)
from backend.app.contracts.responses import AgentResponse, ResponseStatus
from backend.app.contracts.state import AgentState

UpdatesT = TypeVar("UpdatesT", bound=ContractModel)


class OutcomeUpdates(TypedDict):
    last_node_status: ResponseStatus
    last_node_error: AgentError | None
    revision_history: list[RevisionRecord]
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
    previous = state["control"]
    retry = (
        previous.current_agent == agent
        and state["last_node_status"] == "error"
        and state["last_node_error"] is not None
        and state["last_node_error"].retryable
    )
    critique = state["critique"]
    revision = (
        previous.current_agent == "critic"
        and agent in {"planner", "preprocessing", "analysis", "interpretation"}
        and critique is not None
        and critique.decision == "revise"
    )
    history = [record.model_copy(deep=True) for record in state["revision_history"]]
    if revision:
        dataset = state["processed_dataset"] or state["dataset"]
        history.append(
            RevisionRecord(
                target_agent=agent,
                plan_id=state["plan"].plan_id if state["plan"] else None,
                dataset_version=dataset.version,
                result_ids=[result.result_id for result in state["analysis_results"]],
                critique=critique.model_copy(deep=True),
            )
        )
    control = RunControl.model_validate(
        {
            **previous.model_dump(),
            "current_agent": agent,
            "status": "running" if response.status == "success" else response.status,
            "retry_count": previous.retry_count + 1 if retry else 0,
            "revision_count": previous.revision_count + int(revision),
        }
    )
    errors = list(state["errors"])
    if response.error is not None:
        errors.append(response.error)
    return OutcomeUpdates(
        last_node_status=response.status,
        last_node_error=response.error.model_copy(deep=True)
        if response.error
        else None,
        revision_history=history,
        control=control,
        clarification_question=response.clarification_question,
        warnings=[
            warning.model_copy(deep=True)
            for warning in [*state["warnings"], *response.warnings]
        ],
        errors=[error.model_copy(deep=True) for error in errors],
    )
