"""Project existing node outputs into LangGraph state without changing agent APIs."""

import logging
from copy import deepcopy
from typing import TypedDict, cast

from backend.app.agents.analysis.node import analysis_node
from backend.app.agents.critic.agent import CriticModel
from backend.app.agents.critic.node import critic_node
from backend.app.agents.interpretation.node import interpretation_node
from backend.app.agents.interpretation.schema import InterpretationModel
from backend.app.agents.preprocessing.workflow import preprocessing_node
from backend.app.contracts.errors import AgentError, ErrorCode
from backend.app.contracts.models import (
    AgentName,
    AnalysisUpdates,
    Critique,
    InterpretationUpdates,
    RunControl,
    WarningEvent,
)
from backend.app.contracts.responses import AgentResponse
from backend.app.contracts.state import AgentState
from backend.app.tools.registry import ToolRegistry


class _Diagnostics(TypedDict):
    errors: list[AgentError]
    warnings: list[WarningEvent]
    clarification_question: str | None
    control: RunControl


def preprocessing_graph_node(state: AgentState) -> dict[str, object]:
    """Record expected validation and storage failures before stopping the graph."""
    try:
        updates = preprocessing_node(state)
    except (ValueError, OSError) as error:
        return {
            "processed_dataset": None,
            "preprocessing_report": None,
            "control": state["control"].model_copy(
                update={"status": "error", "current_agent": "preprocessing"}
            ),
            "errors": [
                *state["errors"],
                AgentError(
                    code="INVALID_DATA"
                    if isinstance(error, ValueError)
                    else "TOOL_FAILURE",
                    message="Preprocessing input is invalid."
                    if isinstance(error, ValueError)
                    else "Preprocessing could not access dataset storage.",
                    source="preprocessing",
                ),
            ],
        }
    if (
        updates.get("processed_dataset") is None
        or updates.get("preprocessing_report") is None
    ):
        updates = {
            **updates,
            "processed_dataset": None,
            "preprocessing_report": None,
            "errors": [
                *state["errors"],
                AgentError(
                    code="INVALID_OUTPUT",
                    message="Preprocessing did not return a dataset and report.",
                    source="preprocessing",
                ),
            ],
        }
    return {
        **updates,
        "control": state["control"].model_copy(
            update={
                "status": "error" if updates.get("errors") else "running",
                "current_agent": "preprocessing",
            }
        ),
    }


def analysis_graph_node(state: AgentState, registry: ToolRegistry) -> dict[str, object]:
    """Keep calculated results and execution gaps, including on analysis failure."""
    response = analysis_node(state, registry=registry)
    if response.status == "success" and response.updates.execution_report is None:
        response = AgentResponse[AnalysisUpdates](
            status="error",
            updates=response.updates,
            warnings=response.warnings,
            error=AgentError(
                code="INVALID_OUTPUT",
                message="Analysis did not return an execution report.",
                source="analysis",
            ),
        )
    return {
        "analysis_execution_report": response.updates.execution_report,
        "analysis_results": response.updates.analysis_results,
        "artifacts": response.updates.artifacts,
        **_response_diagnostics(state, response, "analysis"),
    }


def interpretation_graph_node(
    state: AgentState, model: InterpretationModel
) -> dict[str, object]:
    """Merge the draft, including explicit clearing on failure, before review."""
    try:
        response = interpretation_node(state, model=model)
    # Unexpected model failures belong at the graph boundary.
    except Exception as error:
        response = AgentResponse[InterpretationUpdates](
            status="error",
            updates=InterpretationUpdates(interpretation=None),
            error=_execution_error(error, "interpretation"),
        )
    if response.status == "success" and response.updates.interpretation is None:
        response = AgentResponse[InterpretationUpdates](
            status="error",
            updates=response.updates,
            warnings=response.warnings,
            error=AgentError(
                code="INVALID_OUTPUT",
                message="Interpretation did not return an interpretation.",
                source="interpretation",
            ),
        )
    diagnostics = _response_diagnostics(state, response, "interpretation")
    critique = state["critique"]
    if (
        state["control"].current_agent == "critic"
        and critique is not None
        and critique.decision == "revise"
    ):
        diagnostics["control"] = diagnostics["control"].model_copy(
            update={"revision_count": state["control"].revision_count + 1}
        )
    return {
        "interpretation": response.updates.interpretation,
        "critique": None,
        **diagnostics,
    }


def critic_graph_node(state: AgentState, model: CriticModel) -> dict[str, object]:
    """Review one draft and record whether a bounded Interpretation revision is valid."""
    try:
        # Critic passes models mutable context; keep authoritative evidence independent.
        updates = critic_node(deepcopy(state), model=model)
        critique = updates.get("critique")
        if critique is not None:
            if not isinstance(critique, Critique):
                raise ValueError("Expected a Critique")
            critique = Critique.model_validate(critique.model_dump())
        errors = cast(list[AgentError], updates.get("errors", state["errors"]))
    except Exception as error:
        critique = None
        errors = [*state["errors"], _execution_error(error, "critic")]
    if errors:
        critique = None
        # The existing Critic adapter can include raw ValueError text.
        errors = [
            *state["errors"],
            *(
                error.model_copy(update={"message": "Critic evaluation failed."})
                for error in errors[len(state["errors"]) :]
            ),
        ]
    else:
        diagnostic = _critique_error(critique, state["control"])
        if diagnostic is not None:
            errors = [diagnostic]
    status = (
        "error"
        if errors
        else "completed"
        if critique.decision == "approved"
        else "running"
    )
    logging.getLogger(__name__).info(
        "critic.reviewed",
        extra={
            "run_id": state["run_id"],
            "node": "critic",
            "critic_decision": critique.decision if critique is not None else None,
            "revision_count": state["control"].revision_count,
            "error_category": errors[-1].code if errors else None,
        },
    )
    return {
        "critique": critique,
        "errors": errors,
        "control": state["control"].model_copy(
            update={"status": status, "current_agent": "critic"}
        ),
    }


def _critique_error(
    critique: Critique | None, control: RunControl
) -> AgentError | None:
    """Validate a review before routing; upstream revision loops are unsupported."""
    if critique is None:
        return AgentError(
            code="INVALID_OUTPUT",
            message="Critic did not return a critique.",
            source="critic",
        )
    if critique.decision == "approved":
        return None
    if critique.decision == "cannot_complete":
        return AgentError(
            code="INSUFFICIENT_DATA",
            message="Critic could not complete review with the available evidence.",
            source="critic",
            details=critique.model_dump(mode="json"),
        )
    targets = sorted(
        {issue.target_agent for issue in critique.issues} - {"interpretation"}
    )
    if targets:
        return AgentError(
            code="INVALID_OUTPUT",
            message="Critique requires changes outside Interpretation; upstream revisions are unsupported.",
            source="critic",
            details={
                "reason": "unsupported_revision_targets",
                "target_agents": targets,
            },
        )
    if not critique.issues or any(
        not issue.description.strip() for issue in critique.issues
    ):
        return AgentError(
            code="INVALID_OUTPUT",
            message="Revision requires an actionable Interpretation-targeted issue.",
            source="critic",
            details={"reason": "missing_actionable_feedback"},
        )
    if control.revision_count >= control.max_revisions:
        return AgentError(
            code="REVISION_LIMIT",
            message="The Interpretation revision limit was reached.",
            source="critic",
            details={
                "revision_count": control.revision_count,
                "max_revisions": control.max_revisions,
            },
        )
    return None


def _execution_error(error: Exception, source: AgentName) -> AgentError:
    """Expose a safe diagnostic without leaking exception messages or retrying."""
    code: ErrorCode = "TOOL_FAILURE"
    if isinstance(error, TimeoutError):
        code = "TIMEOUT"
    elif isinstance(error, ValueError):
        code = "INVALID_OUTPUT"
    return AgentError(
        code=code,
        message=f"The {source} attempt failed.",
        source=source,
        retryable=isinstance(error, (TimeoutError, ConnectionError)),
    )


def _response_diagnostics(
    state: AgentState,
    response: AgentResponse[AnalysisUpdates] | AgentResponse[InterpretationUpdates],
    source: AgentName,
) -> _Diagnostics:
    warnings = list(state["warnings"])
    candidates = response.warnings
    if source == "interpretation":
        # Interpretation re-emits sanitized projections of input warnings.
        # Merge the original events, preserving distinct messages for the same step.
        report = state["preprocessing_report"]
        candidates = [
            *(report.warnings if report is not None else []),
            *(
                warning
                for result in state["analysis_results"]
                for warning in result.warnings
            ),
        ]
    for warning in candidates:
        if warning not in warnings:
            warnings.append(warning)
    errors = list(state["errors"])
    if response.error is not None:
        errors.append(response.error)
    return {
        "warnings": warnings,
        "errors": errors,
        "clarification_question": response.clarification_question,
        "control": state["control"].model_copy(
            update={
                "status": "error"
                if errors
                else "needs_clarification"
                if response.status == "needs_clarification"
                else "running",
                "current_agent": source,
            }
        ),
    }
