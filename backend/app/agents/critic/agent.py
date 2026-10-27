"""Core logic for the Critic Agent."""

from collections.abc import Callable
from pathlib import Path

from backend.app.contracts.errors import AgentError
from backend.app.contracts.models import (
    AnalysisExecutionReport,
    AnalysisResult,
    CriticUpdates,
    Critique,
    Interpretation,
    Plan,
    PreprocessingReport,
    WarningEvent,
)
from backend.app.contracts.responses import AgentResponse

from .schema import CriticContext

PROMPT_PATH = Path(__file__).with_name("prompt.md")


CriticModel = Callable[[str, CriticContext], Critique]


def run_critic(
    user_query: str,
    plan: Plan | None,
    analysis_results: list[AnalysisResult],
    interpretation: Interpretation | None,
    model: CriticModel,
    *,
    preprocessing_report: PreprocessingReport | None = None,
    analysis_execution_report: AnalysisExecutionReport | None = None,
    warnings: list[WarningEvent] | None = None,
) -> AgentResponse[CriticUpdates]:
    """Evaluate an interpretation and return structured feedback."""

    if interpretation is None:
        return AgentResponse(
            status="error",
            updates=CriticUpdates(),
            error=AgentError(
                code="INVALID_DATA",
                message="Critic requires an interpretation",
                source="critic",
            ),
        )

    context = CriticContext(
        user_query=user_query,
        plan=plan,
        analysis_results=analysis_results,
        interpretation=interpretation,
        preprocessing_report=preprocessing_report,
        analysis_execution_report=analysis_execution_report,
        warnings=warnings or [],
    ).model_copy(deep=True)

    prompt = PROMPT_PATH.read_text(encoding="utf-8")

    try:
        critique = model(prompt, context)
    except ValueError as exc:
        return AgentResponse(
            status="error",
            updates=CriticUpdates(),
            error=AgentError(
                code="INVALID_OUTPUT",
                message=str(exc),
                source="critic",
            ),
        )

    return AgentResponse(
        status="success",
        updates=CriticUpdates(critique=critique),
    )
