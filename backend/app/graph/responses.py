"""Translate typed agent responses into workflow state updates."""

from copy import deepcopy
from typing import TypedDict, TypeVar

from backend.app.contracts.errors import AgentError
from backend.app.contracts.models import (
    AgentName,
    AnalysisExecutionReport,
    AnalysisResult,
    AnalysisUpdates,
    Artifact,
    CriticUpdates,
    Critique,
    DatasetReference,
    Interpretation,
    InterpretationUpdates,
    Plan,
    PlannerUpdates,
    PreprocessingReport,
    PreprocessingUpdates,
    RunControl,
    WarningEvent,
)
from backend.app.contracts.responses import AgentResponse, ResponseStatus
from backend.app.contracts.state import AgentState

SupportedUpdates = (
    PlannerUpdates
    | PreprocessingUpdates
    | AnalysisUpdates
    | InterpretationUpdates
    | CriticUpdates
)
UpdatesT = TypeVar("UpdatesT", bound=SupportedUpdates)


class AgentStateUpdate(TypedDict, total=False):
    last_node_status: ResponseStatus
    final_response: None
    plan: Plan | None
    processed_dataset: DatasetReference | None
    preprocessing_report: PreprocessingReport | None
    analysis_execution_report: AnalysisExecutionReport | None
    analysis_results: list[AnalysisResult]
    artifacts: list[Artifact]
    interpretation: Interpretation | None
    critique: Critique | None
    errors: list[AgentError]
    warnings: list[WarningEvent]
    clarification_question: str | None
    control: RunControl


def _map_updates(updates: SupportedUpdates) -> tuple[AgentName, AgentStateUpdate]:
    if isinstance(updates, PlannerUpdates):
        return "planner", {"plan": updates.plan}
    if isinstance(updates, PreprocessingUpdates):
        return "preprocessing", {
            "processed_dataset": updates.processed_dataset,
            "preprocessing_report": updates.preprocessing_report,
        }
    if isinstance(updates, AnalysisUpdates):
        return "analysis", {
            "analysis_execution_report": updates.execution_report,
            "analysis_results": updates.analysis_results,
            "artifacts": updates.artifacts,
        }
    if isinstance(updates, InterpretationUpdates):
        return "interpretation", {"interpretation": updates.interpretation}
    if isinstance(updates, CriticUpdates):
        return "critic", {"critique": updates.critique}
    raise TypeError(f"Unsupported agent updates: {type(updates).__name__}")


def translate_agent_response(
    state: AgentState,
    response: AgentResponse[UpdatesT],
) -> AgentStateUpdate:
    source, updates = _map_updates(response.updates)
    # Preserve invalidation from the draft harness when upstream work is replaced.
    if source == "planner":
        updates.update(processed_dataset=None, preprocessing_report=None)
    if source in {"planner", "preprocessing"}:
        updates.update(
            analysis_execution_report=None, analysis_results=[], artifacts=[]
        )
    if source in {"planner", "preprocessing", "analysis"}:
        updates.update(interpretation=None, critique=None)
    updates["final_response"] = None
    required_output = {
        key: value for key, value in _map_updates(response.updates)[1].items()
    }
    errors = list(state["errors"])
    if response.error is not None:
        errors.append(response.error)
    if response.status == "success":
        # Every nullable output mapped above is required for agent success.
        missing = [name for name, value in required_output.items() if value is None]
        if missing:
            errors.append(
                AgentError(
                    code="INVALID_OUTPUT",
                    message=f"The {source} response omitted required output.",
                    source=source,
                    details={"missing_outputs": missing},
                )
            )
    if errors:
        updates["errors"] = errors

    warnings = list(state["warnings"])
    candidates = response.warnings
    if source == "interpretation":
        # Interpretation returns sanitized projections of existing evidence warnings.
        # Merge originals so changed messages cannot duplicate the same event.
        report = state["preprocessing_report"]
        candidates = [
            *(report.warnings if report is not None else []),
            *(
                warning
                for result in state["analysis_results"]
                for warning in result.warnings
            ),
        ]
        if response.status != "success":
            updates["interpretation"] = None
        updates["critique"] = None
    for warning in candidates:
        if warning not in warnings:
            warnings.append(warning)
    updates["warnings"] = warnings
    updates["clarification_question"] = response.clarification_question
    updates["control"] = state["control"].model_copy(
        update={
            "status": "error"
            if errors
            else "needs_clarification"
            if response.status == "needs_clarification"
            else "running",
            "current_agent": source,
        }
    )
    updates["last_node_status"] = "error" if errors else response.status
    return deepcopy(updates)
