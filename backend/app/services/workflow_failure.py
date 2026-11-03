"""Persist a safe terminal outcome when a background run fails unexpectedly."""

import logging

from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph

from backend.app.contracts.errors import AgentError
from backend.app.contracts.state import AgentState


def persist_failure(
    graph: CompiledStateGraph, config: RunnableConfig, run_id: str
) -> None:
    logging.getLogger(__name__).error("workflow.failed", extra={"run_id": run_id})
    state: AgentState = graph.get_state(config).values
    error = AgentError(
        code="TOOL_FAILURE",
        message="The workflow could not finish. Check the backend configuration and try again.",
        source="harness",
    )
    graph.update_state(
        config,
        {
            "last_node_error": error,
            "last_node_status": "error",
            "final_response": None,
            "errors": [*state["errors"], error],
            "control": state["control"].model_copy(
                update={"status": "error", "current_agent": None}
            ),
        },
        as_node="finish_run",
    )
