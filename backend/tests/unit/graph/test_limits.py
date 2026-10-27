"""Retry budgets reject invalid configuration and permanent error categories."""

import pytest
from pydantic import ValidationError

from backend.app.contracts.errors import AgentError
from backend.app.contracts.models import RunControl
from backend.app.graph.limits import can_retry, workflow_recursion_limit


@pytest.mark.parametrize("field", ["retry_count", "max_retries", "max_revisions"])
def test_limits_reject_negative_values(field):
    with pytest.raises(ValidationError):
        RunControl.model_validate({field: -1})


@pytest.mark.parametrize(
    "code",
    [
        "INVALID_DATA",
        "INVALID_OUTPUT",
        "MISSING_COLUMN",
        "INSUFFICIENT_DATA",
        "REVISION_LIMIT",
    ],
)
def test_permanent_categories_cannot_be_retried_even_if_mislabeled(code):
    error = AgentError(code=code, message="Invalid", source="planner", retryable=True)
    assert not can_retry(error, RunControl(max_retries=2))


def test_recursion_budget_covers_all_node_retries_and_upstream_revisions():
    control = RunControl(max_revisions=3, max_retries=2)
    assert workflow_recursion_limit(control) > 2 + 5 * 4 * 3
