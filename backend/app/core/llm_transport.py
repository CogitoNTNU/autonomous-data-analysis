"""Keep network establishment short while allowing model generation time."""

from math import isfinite

from httpx2 import Timeout


def model_timeout(timeout_seconds: float) -> Timeout:
    if not isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise ValueError("Model timeout must be finite and positive")
    return Timeout(timeout_seconds, connect=min(5.0, timeout_seconds))
