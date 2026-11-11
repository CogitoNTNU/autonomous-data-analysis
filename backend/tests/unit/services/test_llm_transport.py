"""Connection failures must not wait for the model's generation timeout."""

import httpx2
import pytest
from openai import APITimeoutError

from backend.app.core.exceptions import ModelConnectionError
from backend.app.core.llm_errors import raise_model_timeout
from backend.app.core.llm_transport import model_timeout


@pytest.mark.parametrize("seconds,connect", [(120, 5), (75, 5), (2, 2)])
def test_short_connection_deadline_preserves_generation_budget(seconds, connect):
    timeout = model_timeout(seconds)
    assert timeout.read == seconds
    assert timeout.connect == connect


@pytest.mark.parametrize("seconds", [0, -1, float("inf"), float("nan")])
def test_rejects_invalid_timeout_configuration(seconds):
    with pytest.raises(ValueError, match="timeout"):
        model_timeout(seconds)


@pytest.mark.parametrize(
    "cause,expected",
    [(httpx2.ConnectTimeout, ModelConnectionError), (httpx2.ReadTimeout, TimeoutError)],
)
def test_connection_timeout_is_distinguished_from_slow_model_output(cause, expected):
    request = httpx2.Request("POST", "https://provider.invalid/v1/chat/completions")
    error = APITimeoutError(request=request)
    error.__cause__ = cause("private provider response", request=request)

    with pytest.raises(expected) as raised:
        raise_model_timeout(error, "planner")

    assert "private" not in str(raised.value)
