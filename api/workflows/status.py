"""Workflow entrypoint. Requires routing to a persistent backend in production."""

import os
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
os.environ.setdefault("MPLBACKEND", "Agg")
_ROOT = str(Path(__file__).resolve().parents[2])
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.app.api.vercel_entry import handle_post  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        handle_post(self, "/api/workflows/status")

    def log_message(self, format: str, *args: object) -> None:
        return
