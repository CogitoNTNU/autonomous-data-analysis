"""Browser-facing workflow errors retain only safe, actionable context."""

from backend.app.contracts.errors import AgentError
from backend.app.services.workflow_snapshot import _public_error


def test_public_error_explains_invalid_conversion_without_exposing_value() -> None:
    error = AgentError(
        code="INVALID_DATA",
        message="Private diagnostic containing not_available.",
        source="preprocessing",
        step_id="convert-price",
        details={
            "reason": "invalid_value",
            "column": "unit_price",
            "target_type": "float",
            "rejected_value": "not_available",
        },
    )

    public = _public_error(error)

    assert public is not None
    assert public.message == (
        "Preprocessing could not convert values in 'unit_price' to float."
    )
    assert public.details == {}
    assert "not_available" not in public.model_dump_json()


def test_public_error_keeps_unknown_diagnostics_generic() -> None:
    error = AgentError(
        code="TOOL_FAILURE",
        message="Private storage path.",
        source="preprocessing",
        details={"path": "/private/data.csv"},
    )

    public = _public_error(error)

    assert public is not None
    assert public.message == "The preprocessing stage failed (TOOL_FAILURE)."
    assert public.details == {}


def test_public_connection_error_explains_network_requirement_without_raw_details():
    error = AgentError(
        code="TOOL_FAILURE",
        source="planner",
        message="private error",
        retryable=True,
        details={"reason": "model_connection_failed", "private": "secret"},
    )

    public = _public_error(error)

    assert "NTNU VPN" in public.message
    assert public.details == {}
    assert "private" not in public.model_dump_json()
