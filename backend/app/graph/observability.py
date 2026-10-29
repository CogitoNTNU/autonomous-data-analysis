"""Record node timings and outcomes without logging prompts or result values."""

import logging
from collections.abc import Callable
from time import perf_counter

from backend.app.contracts.models import AgentName
from backend.app.contracts.state import AgentState

from .responses import AgentStateUpdate


def measured_node(
    agent: AgentName,
    execute: Callable[[AgentState], AgentStateUpdate],
) -> Callable[[AgentState], AgentStateUpdate]:
    def run(state: AgentState) -> AgentStateUpdate:
        logger = logging.getLogger(__name__)
        retrying = (
            state["control"].current_agent == agent
            and state["last_node_error"] is not None
            and state["last_node_error"].retryable
        )
        retry_count = state["control"].retry_count + int(retrying)
        fields = {
            "run_id": state["run_id"],
            "node": agent,
            "retry_count": retry_count,
            "attempt": retry_count + 1,
            "revision_count": state["control"].revision_count,
        }
        logger.info("workflow.node_started", extra=fields)
        started = perf_counter()
        try:
            updates = execute(state)
        except Exception:
            logger.error(
                "workflow.node_failed",
                extra={
                    **fields,
                    "duration_seconds": round(perf_counter() - started, 3),
                    "error_category": "UNHANDLED",
                },
            )
            raise
        error = updates.get("last_node_error")
        logger.info(
            "workflow.node_finished",
            extra={
                **fields,
                "duration_seconds": round(perf_counter() - started, 3),
                "error_category": error.code if error else None,
            },
        )
        return updates

    return run
