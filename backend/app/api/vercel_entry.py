"""Adapt the planner routes to a Vercel Python function."""

import json
from http.server import BaseHTTPRequestHandler

from backend.app.api.planner_server import PlannerApp, dispatch, make_app

_app: PlannerApp | None = None


def handle_post(handler: BaseHTTPRequestHandler, path: str) -> None:
    status, payload = dispatch(_hosted_app(), path, _body(handler), handler.headers)
    encoded = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(encoded)))
    handler.end_headers()
    handler.wfile.write(encoded)


def _hosted_app() -> PlannerApp:
    global _app
    if _app is None:
        _app = make_app()
    return _app


def _body(handler: BaseHTTPRequestHandler) -> bytes:
    try:
        length = int(handler.headers.get("Content-Length", "0"))
    except ValueError:
        return b""
    if length <= 0:
        return b""
    return handler.rfile.read(length)
