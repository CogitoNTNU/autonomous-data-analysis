"""Public workflow requests and snapshots; clients never submit agent outputs."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, JsonValue, StringConstraints

from .errors import AgentError
from .final_response import FinalResponse
from .models import (
    AgentName,
    ContractModel,
    Critique,
    Interpretation,
    Plan,
    PreprocessingReport,
    WarningEvent,
)

Question = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10000)
]


class StartWorkflow(ContractModel):
    dataset_id: UUID
    question: Question


class WorkflowQuery(ContractModel):
    run_id: UUID


class ResumeWorkflow(WorkflowQuery):
    checkpoint_id: str = Field(min_length=1)
    answer: Question


class FigurePreview(ContractModel):
    artifact_id: str
    image: str


class PublicArtifact(ContractModel):
    artifact_id: str
    type: Literal["figure", "table"]


class PublicAnalysisResult(ContractModel):
    result_id: str
    step_id: str
    dataset_version: str
    method: str
    parameters: dict[str, JsonValue]
    values: dict[str, JsonValue]
    sample_size: int
    warnings: list[WarningEvent]


class AnalysisOutput(ContractModel):
    results: list[PublicAnalysisResult]
    artifacts: list[PublicArtifact]
    figures: list[FigurePreview]
    warnings: list[str]


class WorkflowSnapshot(ContractModel):
    run_id: str
    checkpoint_id: str
    status: Literal["running", "needs_clarification", "completed", "error"]
    active_agent: AgentName | None = None
    question: str | None = None
    plan: Plan | None = None
    report: PreprocessingReport | None = None
    analysis: AnalysisOutput | None = None
    interpretation: Interpretation | None = None
    critique: Critique | None = None
    answer: FinalResponse | None = None
    error: AgentError | None = None
