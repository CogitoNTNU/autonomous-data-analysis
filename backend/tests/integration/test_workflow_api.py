"""The browser runs one authoritative harness, including revisions and clarification."""

import json
import time
from unittest.mock import Mock
from uuid import uuid4

import pytest

from backend.app.agents.planner.schema import ClarificationRequest, PlannerOutput
from backend.app.api.planner_server import PlannerApp, dispatch
from backend.app.contracts.models import Critique


@pytest.fixture
def workflow_app(pipeline_dataset, pipeline_registry, pipeline_models, tmp_path):
    planner, interpretation, critic = pipeline_models
    app = PlannerApp(
        tmp_path,
        pipeline_registry,
        lambda: planner,
        lambda: interpretation,
        lambda: critic,
    )
    from pathlib import Path

    code, registered = dispatch(
        app, "/api/datasets", Path(pipeline_dataset.storage_ref).read_bytes(), {}
    )
    assert code == 200
    pipeline_dataset.dataset_id = registered["dataset_id"]
    yield app
    app.workflows.close()


def post(app, path, payload):
    return dispatch(app, path, json.dumps(payload).encode(), {})


def start(app, dataset):
    code, payload = post(
        app,
        "/api/workflows",
        {"dataset_id": dataset.dataset_id, "question": "Describe age"},
    )
    assert code == 200, payload
    return payload


def settled(app, run_id):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        code, payload = post(app, "/api/workflows/status", {"run_id": run_id})
        assert code == 200, payload
        if payload["status"] != "running":
            return payload
        time.sleep(0.01)
    pytest.fail("Workflow did not settle")


def test_runs_all_agents_and_presents_answer_without_approvals(
    workflow_app, pipeline_dataset, pipeline_models
):
    result = settled(workflow_app, start(workflow_app, pipeline_dataset)["run_id"])

    assert result["status"] == "completed", result
    assert result["report"]["rows_after"] == 2
    assert result["analysis"]["results"][0]["sample_size"] == 2
    assert result["critique"]["decision"] == "approved"
    assert result["answer"]["text"] == result["interpretation"]["summary"]
    assert "storage_ref" not in json.dumps(result)
    for model in pipeline_models:
        assert model.call_count == 1


def test_clarification_resumes_same_checkpoint_and_preserves_context(
    workflow_app, pipeline_dataset, pipeline_models, pipeline_plan
):
    pipeline_models[0].side_effect = [
        PlannerOutput(clarification=ClarificationRequest(question="Which column?")),
        PlannerOutput(plan=pipeline_plan),
    ]
    result = settled(workflow_app, start(workflow_app, pipeline_dataset)["run_id"])
    assert result["status"] == "needs_clarification"
    assert not pipeline_models[1].called
    payload = {
        "run_id": result["run_id"],
        "checkpoint_id": result["checkpoint_id"],
        "answer": "age",
    }
    assert post(workflow_app, "/api/workflows/resume", payload)[0] == 200
    final = settled(workflow_app, result["run_id"])
    assert final["status"] == "completed", final
    assert final["run_id"] == result["run_id"]
    context = pipeline_models[0].call_args.args[1]
    assert context.user_query == "Describe age\nClarification: age"
    assert context.conversation_context[-1].content == "age"
    assert post(workflow_app, "/api/workflows/resume", payload)[0] == 400


def test_critic_revisions_run_automatically_without_repeating_preprocessing(
    workflow_app, pipeline_dataset, pipeline_models, revision_critique
):
    pipeline_models[2].side_effect = [revision_critique, Critique(decision="approved")]
    result = settled(workflow_app, start(workflow_app, pipeline_dataset)["run_id"])

    assert result["status"] == "completed", result
    assert pipeline_models[0].call_count == 1
    assert pipeline_models[1].call_count == 2
    first, second = pipeline_models[1].call_args_list
    assert (
        first.args[1].evidence.results[0].result_id
        == second.args[1].evidence.results[0].result_id
    )


def test_unknown_run_and_client_authored_results_are_rejected(
    workflow_app, pipeline_dataset
):
    assert (
        post(workflow_app, "/api/workflows/status", {"run_id": str(uuid4())})[0] == 400
    )
    code, _ = post(
        workflow_app,
        "/api/workflows",
        {
            "dataset_id": pipeline_dataset.dataset_id,
            "question": "Describe age",
            "plan": {},
        },
    )
    assert code == 422
    assert (
        post(
            workflow_app,
            "/api/workflows",
            {"dataset_id": pipeline_dataset.dataset_id, "question": " "},
        )[0]
        == 422
    )
    assert (
        post(
            workflow_app,
            "/api/workflows/resume",
            {"run_id": str(uuid4()), "checkpoint_id": "old", "answer": " "},
        )[0]
        == 422
    )


def test_checkpoints_survive_app_restart(
    workflow_app, pipeline_dataset, pipeline_registry, tmp_path
):
    result = settled(workflow_app, start(workflow_app, pipeline_dataset)["run_id"])
    forbidden = Mock(side_effect=AssertionError("Reading status must not call models"))
    restarted = PlannerApp(tmp_path, pipeline_registry, forbidden, forbidden, forbidden)
    try:
        assert settled(restarted, result["run_id"]) == result
        forbidden.assert_not_called()
    finally:
        restarted.workflows.close()


def test_worker_failure_is_terminal_and_does_not_leak_provider_errors(
    workflow_app, pipeline_dataset, pipeline_models
):
    pipeline_models[0].side_effect = RuntimeError(
        "private-provider-secret /private/data.csv"
    )
    result = settled(workflow_app, start(workflow_app, pipeline_dataset)["run_id"])
    assert result["status"] == "error"
    assert result["answer"] is None
    assert "private" not in json.dumps(result)
    assert not pipeline_models[1].called


def test_clarification_is_bounded(workflow_app, pipeline_dataset, pipeline_models):
    pipeline_models[0].return_value = PlannerOutput(
        clarification=ClarificationRequest(question="Which column?")
    )
    result = settled(workflow_app, start(workflow_app, pipeline_dataset)["run_id"])
    for _ in range(3):
        assert (
            post(
                workflow_app,
                "/api/workflows/resume",
                {
                    "run_id": result["run_id"],
                    "checkpoint_id": result["checkpoint_id"],
                    "answer": "age",
                },
            )[0]
            == 200
        )
        result = settled(workflow_app, result["run_id"])
    assert result["status"] == "error"
    assert result["error"]["code"] == "REVISION_LIMIT"


def test_storage_failures_return_json_errors(workflow_app, monkeypatch):
    import sqlite3

    monkeypatch.setattr(
        workflow_app.workflows,
        "status",
        Mock(side_effect=sqlite3.OperationalError("private database path")),
    )
    code, result = post(workflow_app, "/api/workflows/status", {"run_id": str(uuid4())})
    assert code == 503
    assert result == {"message": "Workflow storage is unavailable"}


def test_start_cannot_replace_a_registered_dataset(workflow_app, pipeline_dataset):
    from pathlib import Path

    stored = workflow_app.directory / f"{pipeline_dataset.dataset_id}.csv"
    original = stored.read_bytes()
    code, _ = post(
        workflow_app,
        "/api/workflows",
        {
            "dataset_id": pipeline_dataset.dataset_id,
            "question": "Describe age",
            "csv": "age\n999999",
        },
    )
    assert code == 422
    assert Path(stored).read_bytes() == original


def test_completed_state_is_not_terminal_until_worker_releases_the_run(
    workflow_app,
    pipeline_dataset,
):
    from uuid import UUID

    result = settled(workflow_app, start(workflow_app, pipeline_dataset)["run_id"])
    with workflow_app.workflows.store.acquire(result["run_id"]):
        active = workflow_app.workflows.status(UUID(result["run_id"]))
        assert active.status == "running"
    final = workflow_app.workflows.status(UUID(result["run_id"]))
    assert final.status == "completed"
    assert final.checkpoint_id == result["checkpoint_id"]


def test_interpretation_timeouts_retry_once_reuse_client_and_then_stop(
    workflow_app, pipeline_dataset, pipeline_models
):
    model = Mock(side_effect=TimeoutError("private provider timeout"))
    factory = Mock(return_value=model)
    workflow_app.workflows.interpretation = factory
    result = settled(workflow_app, start(workflow_app, pipeline_dataset)["run_id"])

    assert result["status"] == "error"
    assert result["error"]["code"] == "TIMEOUT"
    assert "did not respond in time" in result["error"]["message"]
    assert model.call_count == 2
    factory.assert_called_once()
    model.close.assert_called_once()
    assert pipeline_models[0].call_count == 1
    pipeline_models[2].assert_not_called()
