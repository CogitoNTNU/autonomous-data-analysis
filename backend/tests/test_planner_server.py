"""The planner HTTP server stores a CSV and returns the planner payload."""

import json
import threading
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from backend.app.agents.planner.schema import ClarificationRequest, PlannerOutput
from backend.app.api.planner_server import UPLOADS, serve
from backend.app.contracts.models import Plan, PlanStep
from backend.app.tools.analysis.group_aggregate import TOOL as GROUP_AGGREGATE_TOOL
from backend.app.tools.registry import ToolRegistry

CSV = b"species,body_mass_g\nAdelie,3750\nGentoo,5000\n"


def test_upload_then_plan_returns_the_model_plan() -> None:
    server = serve(
        directory=UPLOADS,
        registry=_registry(),
        model_factory=lambda: _plan_model,
        port=0,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_address[1]}"
        uploaded = _post(base, "/api/datasets", CSV, "text/csv")
        planned = _post(
            base,
            "/api/planner",
            json.dumps(
                {"dataset_id": uploaded["dataset_id"], "question": "Compare mass"}
            ).encode(),
            "application/json",
        )
        assert planned["status"] == "success", planned
        assert planned["plan"]["objective"] == "Compare average body mass"
        assert planned["plan"]["analysis_steps"][0]["tool_name"] == "group_aggregate"
    finally:
        _remove_uploads(server)
        server.shutdown()


def test_plan_restores_a_csv_when_the_upload_is_gone() -> None:
    server = serve(
        directory=UPLOADS,
        registry=_registry(),
        model_factory=lambda: _plan_model,
        port=0,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_address[1]}"
        uploaded = _post(base, "/api/datasets", CSV, "text/csv")
        Path(server.paths[uploaded["dataset_id"]]).unlink()
        server.paths.clear()
        planned = _post(
            base,
            "/api/planner",
            json.dumps(
                {
                    "dataset_id": uploaded["dataset_id"],
                    "question": "Compare mass",
                    "csv": CSV.decode(),
                }
            ).encode(),
            "application/json",
        )
        assert planned["status"] == "success", planned
    finally:
        _remove_uploads(server)
        server.shutdown()


def test_planner_rejects_a_dataset_id_that_is_not_a_uuid() -> None:
    server = serve(
        directory=UPLOADS,
        registry=_registry(),
        model_factory=lambda: _plan_model,
        port=0,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            _post(
                base,
                "/api/planner",
                json.dumps(
                    {
                        "dataset_id": "../secret",
                        "question": "Compare mass",
                        "csv": CSV.decode(),
                    }
                ).encode(),
                "application/json",
            )
        except HTTPError as exc:
            assert exc.code == 400
            assert b"Unknown dataset" in exc.read()
        else:
            raise AssertionError("expected a path-like dataset id to be rejected")
    finally:
        server.shutdown()


def test_unknown_dataset_is_rejected() -> None:
    server = serve(
        directory=UPLOADS,
        registry=_registry(),
        model_factory=lambda: _clarification_model,
        port=0,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            _post(
                base,
                "/api/planner",
                json.dumps(
                    {"dataset_id": "missing", "question": "Compare mass"}
                ).encode(),
                "application/json",
            )
        except HTTPError as exc:
            assert exc.code == 400
            assert b"Unknown dataset" in exc.read()
        else:
            raise AssertionError("expected the unknown dataset to be rejected")
    finally:
        server.shutdown()


def test_clarification_is_returned_without_a_plan() -> None:
    server = serve(
        directory=UPLOADS,
        registry=_registry(),
        model_factory=lambda: _clarification_model,
        port=0,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_address[1]}"
        uploaded = _post(base, "/api/datasets", CSV, "text/csv")
        planned = _post(
            base,
            "/api/planner",
            json.dumps(
                {
                    "dataset_id": uploaded["dataset_id"],
                    "question": "Which are largest?",
                }
            ).encode(),
            "application/json",
        )
        assert planned == {
            "status": "needs_clarification",
            "question": "Which size measure should be used?",
        }
    finally:
        _remove_uploads(server)
        server.shutdown()


def _post(base: str, path: str, body: bytes, content_type: str) -> dict:
    request = Request(
        f"{base}{path}",
        data=body,
        headers={"Content-Type": content_type},
        method="POST",
    )
    for _ in range(20):
        try:
            with urlopen(request) as response:
                return json.load(response)
        except HTTPError:
            raise
        except URLError:
            time.sleep(0.05)
    raise AssertionError("planner server did not accept a connection")


def _registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(GROUP_AGGREGATE_TOOL)
    return registry


def _plan_model(_prompt: str, context: object) -> PlannerOutput:
    del context
    return PlannerOutput(
        plan=Plan(
            plan_id="plan-1",
            objective="Compare average body mass",
            required_columns=["species", "body_mass_g"],
            analysis_steps=[
                PlanStep(
                    step_id="mass",
                    tool_name="group_aggregate",
                    arguments={
                        "group_by": ["species"],
                        "aggregations": [
                            {
                                "column": "body_mass_g",
                                "function": "mean",
                                "alias": "average_body_mass",
                            }
                        ],
                    },
                )
            ],
        )
    )


def _clarification_model(_prompt: str, context: object) -> PlannerOutput:
    del context
    return PlannerOutput(
        clarification=ClarificationRequest(
            question="Which size measure should be used?"
        )
    )


def _remove_uploads(server: object) -> None:
    paths = getattr(server, "paths", {})
    for path in paths.values():
        Path(path).unlink(missing_ok=True)
