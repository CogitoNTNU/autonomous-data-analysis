"""Execution budgets owned by the harness, independent of provider retries."""

from backend.app.contracts.errors import AgentError
from backend.app.contracts.models import RunControl


def can_retry(error: AgentError | None, control: RunControl) -> bool:
    """Invalid inputs cannot be retried even if incorrectly marked retryable."""
    return (
        error is not None
        and error.retryable
        and error.code in {"TIMEOUT", "TOOL_FAILURE"}
        and control.retry_count < control.max_retries
    )


def workflow_recursion_limit(control: RunControl) -> int:
    """Allow all configured attempts plus start/finish and a termination margin."""
    return 3 + 5 * (1 + control.max_revisions) * (1 + control.max_retries)
