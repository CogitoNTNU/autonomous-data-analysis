"""HTTP helpers for driving the workflow API in integration tests."""

import json
import time

import pytest

from backend.app.api.planner_server import PlannerApp, dispatch
from backend.app.contracts.models import DatasetReference


def post(app: PlannerApp, path: str, payload: dict) -> tuple[int, dict]:
    return dispatch(app, path, json.dumps(payload).encode(), {})


def start(app: PlannerApp, dataset: DatasetReference) -> dict:
    code, payload = post(
        app,
        "/api/workflows",
        {"dataset_id": dataset.dataset_id, "question": "Describe age"},
    )
    assert code == 200, payload
    return payload


def settled(app: PlannerApp, run_id: str) -> dict:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        code, payload = post(app, "/api/workflows/status", {"run_id": run_id})
        assert code == 200, payload
        if payload["status"] != "running":
            return payload
        time.sleep(0.01)
    pytest.fail("Workflow did not settle")


def send(app: PlannerApp, snapshot: dict, message: str) -> tuple[int, dict]:
    return post(
        app,
        "/api/workflows/messages",
        {
            "run_id": snapshot["run_id"],
            "checkpoint_id": snapshot["checkpoint_id"],
            "message": message,
        },
    )
