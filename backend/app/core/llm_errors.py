"""Translate provider HTTP failures into safe workflow-level exceptions."""

from typing import NoReturn

from openai import APIStatusError

from backend.app.core.exceptions import ModelProviderError


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
