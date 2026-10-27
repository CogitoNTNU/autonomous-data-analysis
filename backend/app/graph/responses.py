"""Translate typed agent responses into workflow state updates."""

from copy import deepcopy
from typing import TypedDict, TypeVar

from backend.app.contracts.errors import AgentError
from backend.app.contracts.final_response import ChatUpdates, FinalResponse
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
    RevisionRecord,
    RunControl,
    WarningEvent,
)
from backend.app.contracts.responses import AgentResponse, ResponseStatus
from backend.app.contracts.state import AgentState

from .limits import can_retry
from .updates import outcome_updates

SupportedUpdates = (
    PlannerUpdates
    | PreprocessingUpdates
    | AnalysisUpdates
    | InterpretationUpdates
    | CriticUpdates
    | ChatUpdates
)
UpdatesT = TypeVar("UpdatesT", bound=SupportedUpdates)


class AgentStateUpdate(TypedDict, total=False):
    last_node_status: ResponseStatus
    last_node_error: AgentError | None
    revision_history: list[RevisionRecord]
    final_response: FinalResponse | None
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
    if isinstance(updates, ChatUpdates):
        return "chat", {"final_response": updates.final_response}
    raise TypeError(f"Unsupported agent updates: {type(updates).__name__}")


def translate_agent_response(
    state: AgentState,
    response: AgentResponse[UpdatesT],
) -> AgentStateUpdate:
    source, updates = _map_updates(response.updates)
    if response.status == "success":
        missing = [name for name, value in updates.items() if value is None]
        if missing:
            response = AgentResponse(
                status="error",
                updates=response.updates,
                warnings=response.warnings,
                error=AgentError(
                    code="INVALID_OUTPUT",
                    message=f"The {source} response omitted required output.",
                    source=source,
                    details={"missing_outputs": missing},
                ),
            )
    outcome = outcome_updates(state, response, agent=source)
    outcome["warnings"] = _merge_warnings(state, response, source)
    # A pending retry must see exactly the same domain inputs (including revision
    # feedback and the previous draft). The active error prevents forward routing.
    if can_retry(outcome["last_node_error"], outcome["control"]):
        return {**outcome, "final_response": None}

    # Replaced upstream work invalidates every dependent output.
    if source == "planner":
        updates.update(processed_dataset=None, preprocessing_report=None)
    if source in {"planner", "preprocessing"}:
        updates.update(
            analysis_execution_report=None, analysis_results=[], artifacts=[]
        )
    if source in {"planner", "preprocessing", "analysis"}:
        updates.update(interpretation=None, critique=None)
        if (
            response.status == "success"
            and state["critique"] is not None
            and state["critique"].decision == "revise"
        ):
            # Mixed feedback must still reach downstream Interpretation.
            updates["critique"] = state["critique"]
    if source != "chat":
        updates["final_response"] = None
    updates.update(outcome)
    if not outcome["errors"]:
        updates.pop("errors", None)

    if source == "interpretation":
        if response.status != "success":
            updates["interpretation"] = None
        updates["critique"] = None
    return deepcopy(updates)


def _merge_warnings(
    state: AgentState, response: AgentResponse[UpdatesT], source: AgentName
) -> list[WarningEvent]:
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
    for warning in candidates:
        if warning not in warnings:
            warnings.append(warning)
    return [warning.model_copy(deep=True) for warning in warnings]
