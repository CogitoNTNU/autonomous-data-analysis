"""Timing records expose execution health, without prompt or result content."""

import json
import logging
from unittest.mock import Mock

import pytest

from backend.app.contracts.errors import AgentError
from backend.app.contracts.models import DatasetReference
from backend.app.contracts.state import create_initial_state
from backend.app.core.logging import WorkflowLogFormatter
from backend.app.graph.observability import measured_node


def state():
    return create_initial_state(
        "private user question",
        DatasetReference(
            dataset_id="d1", version="v1", storage_ref="private.csv", schema={}
        ),
    )


def test_logs_duration_and_error_category_without_private_diagnostics(
    monkeypatch, caplog
):
    clock = iter([10.0, 11.25])
    monkeypatch.setattr(
        "backend.app.graph.observability.perf_counter", lambda: next(clock)
    )
    error = AgentError(
        code="TIMEOUT",
        message="private provider response",
        source="interpretation",
        retryable=True,
    )
    updates = {"last_node_error": error}
    execute = Mock(return_value=updates)
    request = state()
    with caplog.at_level(logging.INFO):
        assert measured_node("interpretation", execute)(request) is updates

    records = [
        json.loads(WorkflowLogFormatter().format(record)) for record in caplog.records
    ]
    assert records[-1]["duration_seconds"] == 1.25
    assert records[-1]["error_category"] == "TIMEOUT"
    assert records[-1]["run_id"] == request["run_id"]
    assert records[-1]["attempt"] == 1
    assert "private" not in json.dumps(records)


def test_logs_second_attempt_when_harness_retries(caplog):
    request = state()
    request["control"] = request["control"].model_copy(
        update={"current_agent": "interpretation"}
    )
    request["last_node_error"] = AgentError(
        code="TIMEOUT", message="timeout", source="interpretation", retryable=True
    )
    with caplog.at_level(logging.INFO):
        measured_node("interpretation", lambda state: {"last_node_error": None})(
            request
        )
    assert caplog.records[-1].attempt == 2


def test_unhandled_failure_is_logged_and_propagated(caplog):
    execute = Mock(side_effect=RuntimeError("private diagnostic"))
    with pytest.raises(RuntimeError), caplog.at_level(logging.INFO):
        measured_node("interpretation", execute)(state())
    assert caplog.records[-1].getMessage() == "workflow.node_failed"
    assert caplog.records[-1].error_category == "UNHANDLED"
    assert "private" not in WorkflowLogFormatter().format(caplog.records[-1])
