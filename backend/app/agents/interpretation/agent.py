"""Execute one interpretation attempt with an injected model and no retries."""

import logging
from pathlib import Path

from backend.app.contracts.errors import AgentError, ErrorCode
from backend.app.contracts.models import (
    Interpretation,
    InterpretationUpdates,
    WarningEvent,
)
from backend.app.contracts.responses import AgentResponse
from backend.app.core.exceptions import ModelProviderError

from .context import build_context, serialize_context
from .evidence import prepare_evidence
from .schema import InterpretationContext, InterpretationInput, InterpretationModel
from .validation import preserve_required_context


def run_interpretation(
    request: InterpretationInput,
    model: InterpretationModel,
) -> AgentResponse[InterpretationUpdates]:
    """Return one grounded draft or a safe structured failure.

    The injected model returns Interpretation, raises ValueError for invalid
    output, or translates transient provider failures to TimeoutError or
    ConnectionError. Permanent provider failures raise ModelProviderError.
    Unexpected exceptions propagate to the workflow boundary.
    Successful drafts still require Critic review; this function never retries.
    """
    logger = logging.getLogger(__name__)
    identifiers = {
        "run_id": request.run_id,
        "plan_id": request.plan.plan_id,
        "dataset_version": request.dataset_version,
        "node": "interpretation",
    }
    logger.info("interpretation.entered", extra=identifiers)
    response = _run_attempt(request, model)
    logger.info(
        "interpretation.exited",
        extra={
            **identifiers,
            "status": response.status,
            "warning_count": len(response.warnings),
            "error_code": response.error.code if response.error else None,
        },
    )
    return response


def _run_attempt(
    request: InterpretationInput,
    model: InterpretationModel,
) -> AgentResponse[InterpretationUpdates]:
    try:
        request = InterpretationInput.model_validate(request.model_dump())
        context = build_context(request, prepare_evidence(request))
        serialize_context(context)
    except ValueError:
        return _failure("INVALID_DATA", "Interpretation input or evidence is invalid.")

    if not context.evidence.results:
        return _failure(
            "INSUFFICIENT_DATA",
            "No usable analysis evidence is available.",
            warnings=context.evidence.warnings,
        )
    try:
        prompt = Path(__file__).with_name("prompt.md").read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return _failure(
            "TOOL_FAILURE",
            "The interpretation prompt could not be loaded.",
            warnings=context.evidence.warnings,
        )
    return _generate_interpretation(prompt, context, model)


def _generate_interpretation(
    prompt: str,
    context: InterpretationContext,
    model: InterpretationModel,
) -> AgentResponse[InterpretationUpdates]:
    try:
        # Keep authoritative evidence independent of any mutations by the adapter.
        draft = model(prompt, context.model_copy(deep=True))
        if not isinstance(draft, Interpretation):
            raise ValueError("The model must return an Interpretation")
        interpretation = preserve_required_context(draft, context)
    except TimeoutError:
        return _failure(
            "TIMEOUT",
            "The interpretation model timed out.",
            warnings=context.evidence.warnings,
            retryable=True,
        )
    except ConnectionError:
        return _failure(
            "TOOL_FAILURE",
            "The interpretation model is temporarily unavailable.",
            warnings=context.evidence.warnings,
            retryable=True,
        )
    except ModelProviderError:
        return _failure(
            "TOOL_FAILURE",
            "The interpretation model request was rejected.",
            warnings=context.evidence.warnings,
        )
    except ValueError:
        return _failure(
            "INVALID_OUTPUT",
            "The interpretation model returned an invalid draft.",
            warnings=context.evidence.warnings,
        )
    return AgentResponse[InterpretationUpdates](
        status="success",
        updates=InterpretationUpdates(interpretation=interpretation),
        warnings=context.evidence.warnings,
    )


def _failure(
    code: ErrorCode,
    message: str,
    *,
    warnings: list[WarningEvent] | None = None,
    retryable: bool = False,
) -> AgentResponse[InterpretationUpdates]:
    return AgentResponse[InterpretationUpdates](
        status="error",
        updates=InterpretationUpdates(),
        warnings=warnings if warnings is not None else [],
        error=AgentError(
            code=code,
            message=message,
            source="interpretation",
            retryable=retryable,
        ),
    )
