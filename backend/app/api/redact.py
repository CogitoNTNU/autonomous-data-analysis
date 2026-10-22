"""Remove secret values before a planner message reaches the browser."""

import os
import re

_SECRET_NAMES = ("NTNU_LLM_API_KEY", "IDUN_API_KEY")
_KEY = re.compile(r"sk-[A-Za-z0-9*_-]{6,}")


def redact(message: str) -> str:
    cleaned = message
    for name in _SECRET_NAMES:
        secret = os.getenv(name, "").strip()
        if len(secret) >= 8:
            cleaned = cleaned.replace(secret, "[redacted]")
    return _KEY.sub("[redacted]", cleaned)
