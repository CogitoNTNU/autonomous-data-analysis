"""Validated payloads shared by all agents; datasets remain in external storage."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue

AgentName = Literal[
    "planner", "preprocessing", "analysis", "interpretation", "critic", "chat"
]
NonEmptyString = Annotated[str, Field(min_length=1)]


class ContractModel(BaseModel):
    """Reject misspelled fields rather than silently dropping model output."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class WarningEvent(ContractModel):
    code: NonEmptyString
    message: NonEmptyString
    source: NonEmptyString
    step_id: str | None = None


class DatasetReference(ContractModel):
    dataset_id: NonEmptyString
    version: NonEmptyString
    storage_ref: NonEmptyString
    # `schema` is a legacy BaseModel method; preserve the wire name via an alias.
    dataset_schema: dict[str, JsonValue] = Field(alias="schema")


class ConversationMessage(ContractModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str


class PlanStep(ContractModel):
    step_id: NonEmptyString
    tool_name: NonEmptyString
    arguments: dict[str, JsonValue] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)


class Plan(ContractModel):
    plan_id: NonEmptyString
    objective: NonEmptyString
    required_columns: list[str] = Field(default_factory=list)
    preprocessing_steps: list[PlanStep] = Field(default_factory=list)
    analysis_steps: list[PlanStep] = Field(default_factory=list)
    expected_outputs: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)


class PreprocessingReport(ContractModel):
    changes: list[str] = Field(default_factory=list)
    affected_columns: list[str] = Field(default_factory=list)
    rows_before: int = Field(ge=0)
    rows_after: int = Field(ge=0)
    warnings: list[WarningEvent] = Field(default_factory=list)


class ResultReference(ContractModel):
    storage_ref: NonEmptyString


class AnalysisResult(ContractModel):
    result_id: NonEmptyString
    step_id: NonEmptyString
    dataset_version: NonEmptyString
    method: NonEmptyString
    parameters: dict[str, JsonValue] = Field(default_factory=dict)
    values: dict[str, JsonValue] | ResultReference
    sample_size: int = Field(ge=0)
    warnings: list[WarningEvent] = Field(default_factory=list)


class Artifact(ContractModel):
    artifact_id: NonEmptyString
    type: Literal["figure", "table"]
    storage_ref: NonEmptyString


class Finding(ContractModel):
    claim: NonEmptyString
    result_ids: list[NonEmptyString] = Field(min_length=1)


class Interpretation(ContractModel):
    summary: NonEmptyString
    findings: list[Finding] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    unanswered_questions: list[str] = Field(default_factory=list)


class CritiqueIssue(ContractModel):
    code: NonEmptyString
    severity: Literal["info", "warning", "error"]
    description: NonEmptyString
    target_agent: AgentName
    related_ids: list[str] = Field(default_factory=list)


class Critique(ContractModel):
    decision: Literal["approved", "revise", "cannot_complete"]
    issues: list[CritiqueIssue] = Field(default_factory=list)
    required_changes: list[str] = Field(default_factory=list)


class FinalResponse(ContractModel):
    text: NonEmptyString
    artifact_ids: list[str] = Field(default_factory=list)
    follow_up_suggestions: list[str] = Field(default_factory=list)


class RunControl(ContractModel):
    status: Literal[
        "pending", "running", "needs_clarification", "completed", "error"
    ] = "pending"
    current_agent: AgentName | None = None
    revision_count: int = Field(default=0, ge=0)
    max_revisions: int = Field(default=2, ge=0)


class PlannerUpdates(ContractModel):
    plan: Plan | None = None


class PreprocessingUpdates(ContractModel):
    processed_dataset: DatasetReference | None = None
    preprocessing_report: PreprocessingReport | None = None


class AnalysisUpdates(ContractModel):
    analysis_results: list[AnalysisResult] = Field(default_factory=list)
    artifacts: list[Artifact] = Field(default_factory=list)


class InterpretationUpdates(ContractModel):
    interpretation: Interpretation | None = None


class CriticUpdates(ContractModel):
    critique: Critique | None = None


class ChatUpdates(ContractModel):
    final_response: FinalResponse | None = None
