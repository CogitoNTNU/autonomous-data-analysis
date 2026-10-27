"""HTTP boundary for starting, observing, and clarifying harness runs."""

import json
import os
import sqlite3
from typing import TYPE_CHECKING

from pydantic import ValidationError

from backend.app.contracts.workflow import ResumeWorkflow, StartWorkflow, WorkflowQuery
from backend.app.services.workflow_dataset import workflow_dataset

if TYPE_CHECKING:
    from backend.app.api.planner_server import PlannerApp

ROUTES = {"/api/workflows", "/api/workflows/status", "/api/workflows/resume"}


def dispatch_workflow(
    app: "PlannerApp", path: str, body: bytes
) -> tuple[int, dict[str, object]]:
    # Ephemeral serverless files cannot safely hold a multi-request workflow.
    if os.getenv("VERCEL"):
        return 503, {
            "message": "Workflows require the persistent backend server. Route /api/workflows to that server."
        }
    try:
        if path == "/api/workflows":
            request = StartWorkflow.model_validate_json(body)
            result = app.workflows.start(
                workflow_dataset(app.directory, request.dataset_id), request.question
            )
        elif path == "/api/workflows/resume":
            result = app.workflows.resume(ResumeWorkflow.model_validate_json(body))
        else:
            result = app.workflows.status(
                WorkflowQuery.model_validate_json(body).run_id
            )
    except (ValidationError, json.JSONDecodeError):
        return 422, {"message": "Invalid workflow request"}
    except ValueError as error:
        return 400, {"message": str(error)}
    except (OSError, sqlite3.Error):
        return 503, {"message": "Workflow storage is unavailable"}
    return 200, result.model_dump(mode="json")
