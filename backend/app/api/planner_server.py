"""HTTP server that accepts a CSV and returns a planner result."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from backend.app.agents.critic.agent import CriticModel
from backend.app.agents.interpretation.schema import InterpretationModel
from backend.app.agents.planner.agent import PlannerModel
from backend.app.agents.planner.llm import PlannerLLM
from backend.app.agents.preprocessing import register_preprocessing_tools
from backend.app.api.origins import Headers, require_site_origin
from backend.app.api.redact import redact
from backend.app.api.workflows import ROUTES, dispatch_workflow
from backend.app.contracts.models import ConversationMessage
from backend.app.core.logging import configure_workflow_logging
from backend.app.services.analysis_request import analyze_plan
from backend.app.services.chat_request import present_answer
from backend.app.services.critic_request import (
    critique_interpretation,
    live_critic_model,
)
from backend.app.services.dataset_lookup import resolve_dataset
from backend.app.services.interpretation_request import (
    interpret_results,
    live_interpretation_model,
)
from backend.app.services.llm_env import ensure_llm_environment
from backend.app.services.planner_request import plan_question
from backend.app.services.preprocessing_request import preprocess_plan
from backend.app.services.uploads import save_csv
from backend.app.services.workflows import WorkflowService
from backend.app.storage.datasets import HOSTED_UPLOADS, create_dataset_reference
from backend.app.storage.workflow_checkpoints import WorkflowCheckpoints
from backend.app.tools.analysis.descriptive import default_registry
from backend.app.tools.dataset.inspection import inspection_registry
from backend.app.tools.registry import ToolRegistry

HOST = "127.0.0.1"
PORT = 8000
UPLOADS = Path(__file__).resolve().parents[2] / "data" / "uploads"
MAX_BODY_BYTES = 11 * 1024 * 1024
PlannerFactory = Callable[[], PlannerModel]
InterpretationFactory = Callable[[], InterpretationModel]
CriticFactory = Callable[[], CriticModel]


class PlannerApp:
    def __init__(
        self,
        directory: Path,
        registry: ToolRegistry,
        model_factory: PlannerFactory,
        interpretation_factory: InterpretationFactory | None = None,
        critic_factory: CriticFactory | None = None,
    ) -> None:
        self.directory = directory
        self.registry = registry
        self.model_factory = model_factory
        self.interpretation_factory = (
            interpretation_factory or live_interpretation_model
        )
        self.critic_factory = critic_factory or live_critic_model
        self.paths: dict[str, Path] = {}
        self.workflows = WorkflowService(
            WorkflowCheckpoints(directory / ".workflows"),
            registry,
            model_factory,
            self.interpretation_factory,
            self.critic_factory,
        )


class PlannerSite(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], app: PlannerApp) -> None:
        self.app = app
        super().__init__(address, PlannerHandler)

    def server_close(self) -> None:
        self.app.workflows.close()
        super().server_close()

    @property
    def paths(self) -> dict[str, Path]:
        return self.app.paths


class PlannerHandler(BaseHTTPRequestHandler):
    server: PlannerSite

    def do_POST(self) -> None:
        try:
            body = _body(self)
        except ValueError as exc:
            _send(self, 400, {"message": redact(str(exc))})
            return
        status, payload = dispatch(self.server.app, self.path, body, self.headers)
        _send(self, status, payload)

    def log_message(self, format: str, *args: object) -> None:
        return


def make_app(
    directory: Path | None = None,
    registry: ToolRegistry | None = None,
    model_factory: PlannerFactory | None = None,
) -> PlannerApp:
    return PlannerApp(
        upload_directory() if directory is None else directory,
        registry or register_preprocessing_tools(default_registry()),
        model_factory or _live_model,
    )


def serve(
    directory: Path = UPLOADS,
    registry: ToolRegistry | None = None,
    model_factory: PlannerFactory | None = None,
    port: int = PORT,
) -> PlannerSite:
    return PlannerSite((HOST, port), make_app(directory, registry, model_factory))


def main() -> None:
    configure_workflow_logging()
    serve(directory=upload_directory()).serve_forever()


def upload_directory() -> Path:
    if os.getenv("VERCEL"):
        return HOSTED_UPLOADS
    return UPLOADS


def dispatch(
    app: PlannerApp,
    path: str,
    body: bytes,
    headers: Headers,
) -> tuple[int, dict[str, object]]:
    if len(body) > MAX_BODY_BYTES:
        return 400, {"message": "The request is too large"}
    try:
        require_site_origin(headers)
        if path.split("?", 1)[0] in ROUTES:
            return dispatch_workflow(app, path.split("?", 1)[0], body)
        payload = _route(app, path.split("?", 1)[0], body)
    except (KeyError, UnicodeError, ValueError) as exc:
        return 400, {"message": redact(str(exc))}
    if payload is None:
        return 404, {"message": "Unknown path"}
    return 200, _public(payload)


def _live_model() -> PlannerLLM:
    ensure_llm_environment()
    return PlannerLLM(inspection_registry=inspection_registry())


def _route(app: PlannerApp, path: str, body: bytes) -> dict[str, object] | None:
    if path == "/api/datasets":
        return _store_dataset(app, body)
    if path == "/api/planner":
        return _plan(app, body)
    if path == "/api/preprocessing":
        return _preprocess(app, body)
    if path == "/api/analysis":
        return _analysis(app, body)
    if path == "/api/interpretation":
        return _interpretation(app, body)
    if path == "/api/critic":
        return _critic(app, body)
    if path == "/api/chat":
        return _chat(body)
    return None


def _body(handler: PlannerHandler) -> bytes:
    try:
        length = int(handler.headers.get("Content-Length", "0"))
    except ValueError as exc:
        raise ValueError("Missing request body") from exc
    if length < 0:
        raise ValueError("Missing request body")
    return handler.rfile.read(length)


def _store_dataset(app: PlannerApp, body: bytes) -> dict[str, str]:
    path = save_csv(app.directory, body)
    try:
        dataset = create_dataset_reference(path)
    except (OSError, UnicodeError, ValueError) as exc:
        path.unlink(missing_ok=True)
        raise ValueError(str(exc)) from exc
    app.paths[dataset.dataset_id] = path
    return {"dataset_id": dataset.dataset_id, "version": dataset.version}


def _plan(app: PlannerApp, body: bytes) -> dict[str, object]:
    request = _object(body)
    path = resolve_dataset(app.directory, app.paths, request)
    messages = [
        ConversationMessage.model_validate(item) for item in request.get("messages", [])
    ]
    try:
        model = app.model_factory()
        return plan_question(
            create_dataset_reference(path),
            str(request.get("question", "")),
            messages,
            app.registry,
            model,
        )
    except KeyError as exc:
        setting = exc.args[0] if exc.args else "NTNU_LLM_API_KEY"
        return {
            "status": "error",
            "message": f"Set {setting} before asking the planner.",
        }
    except ValueError:
        raise
    except Exception as exc:  # noqa: BLE001 - the page shows the planner failure
        return {"status": "error", "message": str(exc) or type(exc).__name__}


def _preprocess(app: PlannerApp, body: bytes) -> dict[str, object]:
    request = _object(body)
    path = resolve_dataset(app.directory, app.paths, request)
    return _captured(
        lambda: preprocess_plan(create_dataset_reference(path), request.get("plan"))
    )


def _analysis(app: PlannerApp, body: bytes) -> dict[str, object]:
    request = _object(body)
    path = resolve_dataset(app.directory, app.paths, request)
    return _captured(
        lambda: analyze_plan(create_dataset_reference(path), request.get("plan"))
    )


def _interpretation(app: PlannerApp, body: bytes) -> dict[str, object]:
    request = _object(body)
    path = resolve_dataset(app.directory, app.paths, request)
    model = _model(app.interpretation_factory)
    if isinstance(model, dict):
        return model
    return _captured(
        lambda: interpret_results(create_dataset_reference(path), request, model)
    )


def _critic(app: PlannerApp, body: bytes) -> dict[str, object]:
    request = _object(body)
    model = _model(app.critic_factory)
    if isinstance(model, dict):
        return model
    return _captured(lambda: critique_interpretation(request, model))


def _chat(body: bytes) -> dict[str, object]:
    return _captured(lambda: present_answer(_object(body)))


def _model(factory: Callable[[], object]) -> object:
    try:
        return factory()
    except KeyError as exc:
        setting = exc.args[0] if exc.args else "NTNU_LLM_API_KEY"
        return {
            "status": "error",
            "message": f"Set {setting} before asking the planner.",
        }


def _captured(action: Callable[[], dict[str, object]]) -> dict[str, object]:
    try:
        return action()
    except ValueError:
        raise
    except Exception as exc:  # noqa: BLE001 - the page shows the agent failure
        return {"status": "error", "message": str(exc) or type(exc).__name__}


def _object(body: bytes) -> dict[str, object]:
    request = json.loads(body.decode("utf-8"))
    if not isinstance(request, dict):
        raise ValueError("Expected a JSON object")  # noqa: TRY004 - HTTP validation errors use ValueError
    return request


def _public(payload: dict[str, object]) -> dict[str, object]:
    message = payload.get("message")
    if isinstance(message, str):
        return {**payload, "message": redact(message)}
    return payload


def _send(handler: PlannerHandler, status: int, payload: dict[str, object]) -> None:
    encoded = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(encoded)))
    handler.end_headers()
    handler.wfile.write(encoded)


if __name__ == "__main__":
    main()
