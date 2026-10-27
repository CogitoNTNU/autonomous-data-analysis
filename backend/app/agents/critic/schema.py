"""Evidence available to one Critic review, without tool or storage access."""

from pydantic import Field

from backend.app.contracts.models import (
    AnalysisExecutionReport,
    AnalysisResult,
    ContractModel,
    Interpretation,
    Plan,
    PreprocessingReport,
    WarningEvent,
)


class CriticContext(ContractModel):
    user_query: str
    plan: Plan | None
    analysis_results: list[AnalysisResult]
    interpretation: Interpretation
    preprocessing_report: PreprocessingReport | None = None
    analysis_execution_report: AnalysisExecutionReport | None = None
    warnings: list[WarningEvent] = Field(default_factory=list)
