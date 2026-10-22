"""Vercel route that runs analysis for a reviewed plan."""

import os
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
os.environ.setdefault("MPLBACKEND", "Agg")
_ROOT = str(Path(__file__).resolve().parents[1])
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import matplotlib  # noqa: E402, F401 - the hosted analysis bundle must include matplotlib

from backend.app.api.vercel_entry import handle_post  # noqa: E402


class handler(BaseHTTPRequestHandler):  # noqa: N801 - Vercel entrypoint name
    def do_POST(self) -> None:  # noqa: N802 - stdlib handler name
        handle_post(self, "/api/analysis")

    def log_message(self, format: str, *args: object) -> None:
        return
