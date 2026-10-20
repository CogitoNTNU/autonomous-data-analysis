"""Translate typed agent responses into workflow state updates."""

from typing import TypedDict, TypeVar

from backend.app.contracts.errors import AgentError
from backend.app.contracts.models import (
    AnalysisExecutionReport,
    AnalysisResult,
    AnalysisUpdates,
    Artifact,
    DatasetReference,
    Interpretation,
    InterpretationUpdates,
    Plan,
    PlannerUpdates,
    PreprocessingReport,
    PreprocessingUpdates,
    WarningEvent,
)
from backend.app.contracts.responses import AgentResponse
from backend.app.contracts.state import AgentState

SupportedUpdates = (
    PlannerUpdates
    | PreprocessingUpdates
    | AnalysisUpdates
    | InterpretationUpdates
)
UpdatesT = TypeVar("UpdatesT", bound=SupportedUpdates)


class AgentStateUpdate(TypedDict, total=False):
    plan: Plan | None
    processed_dataset: DatasetReference | None
    preprocessing_report: PreprocessingReport | None
    analysis_execution_report: AnalysisExecutionReport | None
    analysis_results: list[AnalysisResult]
    artifacts: list[Artifact]
    interpretation: Interpretation | None
    errors: list[AgentError]
    warnings: list[WarningEvent]
    clarification_question: str | None


def _map_updates(updates: SupportedUpdates) -> AgentStateUpdate:
    if isinstance(updates, PlannerUpdates):
        return {"plan": updates.plan}

    if isinstance(updates, PreprocessingUpdates):
        return {
            "processed_dataset": updates.processed_dataset,
            "preprocessing_report": updates.preprocessing_report,
        }

    if isinstance(updates, AnalysisUpdates):
        return {
            "analysis_execution_report": updates.execution_report,
            "analysis_results": updates.analysis_results,
            "artifacts": updates.artifacts,
        }

    if isinstance(updates, InterpretationUpdates):
        return {"interpretation": updates.interpretation}

    raise TypeError(
        f"Unsupported agent updates: {type(updates).__name__}"
    )


def translate_agent_response(
    state: AgentState,
    response: AgentResponse[UpdatesT],
) -> AgentStateUpdate:
    updates = _map_updates(response.updates)

    updates["warnings"] = [*state["warnings"], *response.warnings]
    updates["clarification_question"] = response.clarification_question

    if response.error is not None:
        updates["errors"] = [*state["errors"], response.error]

    return updates