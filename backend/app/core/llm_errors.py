"""Translate provider HTTP failures into safe workflow-level exceptions."""

from typing import NoReturn

from httpx2 import ConnectTimeout
from openai import APIStatusError, APITimeoutError

from backend.app.core.exceptions import ModelConnectionError, ModelProviderError


def raise_model_timeout(error: APITimeoutError, source: str) -> NoReturn:
    if isinstance(error.__cause__, ConnectTimeout):
        raise ModelConnectionError(f"The {source} provider is unreachable") from error
    raise TimeoutError(f"The {source} model timed out") from error


def raise_provider_error(error: APIStatusError, source: str) -> NoReturn:
    """Keep transient outages retryable without retrying credentials or quota."""
    if error.status_code == 408:
        raise TimeoutError(f"The {source} provider timed out") from error
    if error.code in {"insufficient_quota", "billing_hard_limit_reached"}:
        raise ModelProviderError(
            "The model request exceeded the provider quota"
        ) from error
    if error.status_code in {409, 429} or 500 <= error.status_code < 600:
        raise ConnectionError(
            f"The {source} provider is temporarily unavailable"
        ) from error
    raise ModelProviderError(f"The {source} provider rejected the request") from error
