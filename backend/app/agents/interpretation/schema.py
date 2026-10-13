from collections.abc import Callable
from typing import Literal

from pydantic import Field, FiniteFloat, JsonValue

from backend.app.contracts.models import (
    AnalysisResult,
    Artifact,
    ContractModel,
    Critique,
    Interpretation,
    NonEmptyString,
    Plan,
    PreprocessingReport,
    WarningEvent,
)


class InterpretationInput(ContractModel):
    run_id: NonEmptyString
    user_query: NonEmptyString
    plan: Plan
    dataset_version: NonEmptyString
    analysis_results: list[AnalysisResult]
    artifacts: list[Artifact]
    preprocessing_report: PreprocessingReport | None = None
    warnings: list[WarningEvent] = Field(default_factory=list)
    previous_interpretation: Interpretation | None = None
    critique: Critique | None = None


class ResultEvidence(ContractModel):
    result_id: NonEmptyString
    step_id: NonEmptyString
    dataset_version: NonEmptyString
    method: NonEmptyString
    parameters: dict[str, JsonValue]
    values: dict[str, JsonValue]
    sample_size: int = Field(ge=0)
    warnings: list[WarningEvent] = Field(default_factory=list)


class InterpretationEvidence(ContractModel):
    results: list[ResultEvidence] = Field(default_factory=list)
    failed_step_ids: list[NonEmptyString] = Field(default_factory=list)
    missing_step_ids: list[NonEmptyString] = Field(default_factory=list)
    unavailable_result_ids: list[NonEmptyString] = Field(default_factory=list)
    warnings: list[WarningEvent] = Field(default_factory=list)
    required_limitations: list[NonEmptyString] = Field(default_factory=list)


class ArtifactContext(ContractModel):
    artifact_id: NonEmptyString
    type: Literal["figure", "table"]


class InterpretationContext(ContractModel):
    user_query: NonEmptyString
    objective: NonEmptyString
    assumptions: list[str]
    expected_outputs: list[str]
    evidence: InterpretationEvidence
    artifacts: list[ArtifactContext]
    preprocessing_report: PreprocessingReport | None = None
    previous_interpretation: Interpretation | None = None
    revision_feedback: list[str] = Field(default_factory=list)


class ColumnStatistics(ContractModel):
    mean: FiniteFloat | None
    median: FiniteFloat | None
    std: FiniteFloat | None
    min: FiniteFloat | None
    max: FiniteFloat | None
    n: int = Field(ge=0)
    missing_rate: float = Field(ge=0, le=1)


class DescriptiveEvidence(ContractModel):
    columns: dict[NonEmptyString, ColumnStatistics]
    status: Literal["ok", "partial"]


ResultAvailability = Literal[
    "usable",
    "partial",
    "failed",
    "external",
]

InterpretationModel = Callable[
    [str, InterpretationContext],
    Interpretation,
]
