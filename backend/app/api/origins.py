"""Reject browser calls that do not come from this hosted site."""

import os
from typing import Protocol


class Headers(Protocol):
    def get(self, name: str, default: str | None = None) -> str | None: ...


def require_site_origin(headers: Headers) -> None:
    if not os.getenv("VERCEL"):
        return
    host = _host(headers)
    origin = headers.get("Origin") or ""
    if host and origin == f"https://{host}":
        return
    raise ValueError("The planner only accepts requests from this site")


def _host(headers: Headers) -> str:
    forwarded = headers.get("X-Forwarded-Host") or headers.get("Host") or ""
    return forwarded.split(",")[0].strip()
