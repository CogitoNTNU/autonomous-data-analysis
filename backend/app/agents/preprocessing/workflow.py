"""Adapters between the shared workflow contracts and the CSV executor."""

from __future__ import annotations

import hashlib
from pathlib import Path

from backend.app.contracts.models import (
    AgentName,
    DatasetReference as WorkflowDatasetReference,
    PlanStep as WorkflowPlanStep,
    PreprocessingReport as WorkflowPreprocessingReport,
    WarningEvent,
)
from backend.app.contracts.state import AgentState
from backend.app.models.dataset import DatasetReference
from backend.app.models.plan import PlanStep
from backend.app.models.results import PreprocessingReport
from backend.app.storage.datasets import create_dataset_reference
from backend.app.tools.preprocessing_tools import build_metadata, load_csv

from .node import run_preprocessing
from .schemas import PreprocessingInput

PREPROCESSING_SOURCE: AgentName = "preprocessing"


def run_shared_preprocessing(
    dataset: WorkflowDatasetReference,
    steps: list[WorkflowPlanStep],
) -> tuple[WorkflowDatasetReference, WorkflowPreprocessingReport]:
    """Execute Planner steps and return the contracts shared with Analysis."""
    internal_dataset = _to_internal_dataset(dataset)
    internal_steps = [PlanStep.model_validate(step.model_dump()) for step in steps]
    result = run_preprocessing(
        PreprocessingInput(dataset=internal_dataset, steps=internal_steps)
    )
    return _to_workflow_dataset(result.processed_dataset), _to_workflow_report(
        result.report
    )


def _to_internal_dataset(dataset: WorkflowDatasetReference) -> DatasetReference:
    safe_reference = create_dataset_reference(
        dataset.storage_ref,
        version=dataset.version,
    )
    fieldnames, rows = load_csv(safe_reference.storage_ref)
    metadata = build_metadata(fieldnames, rows)
    source_path = Path(safe_reference.storage_ref)
    return DatasetReference(
        dataset_id=dataset.dataset_id,
        version=dataset.version,
        uri=safe_reference.storage_ref,
        format="csv",
        content_hash=hashlib.sha256(source_path.read_bytes()).hexdigest(),
        metadata=metadata,
    )


def _to_workflow_dataset(output: DatasetReference) -> WorkflowDatasetReference:
    return WorkflowDatasetReference(
        dataset_id=output.dataset_id,
        version=output.version,
        storage_ref=output.uri,
        schema={
            column.name: {
                "datatype": column.data_type,
                "missing_count": column.missing_count,
            }
            for column in output.metadata.columns
        },
    )


def _to_workflow_report(report: PreprocessingReport) -> WorkflowPreprocessingReport:
    return WorkflowPreprocessingReport(
        changes=[
            f"{change.step_id} ({change.tool_name}): {change.description}"
            for change in report.changes
        ],
        affected_columns=report.affected_columns,
        rows_before=report.rows_before,
        rows_after=report.rows_after,
        warnings=[
            WarningEvent(
                code="PREPROCESSING_WARNING",
                message=warning,
                source=PREPROCESSING_SOURCE,
            )
            for warning in report.quality_warnings
        ],
    )


def preprocessing_node(state: AgentState) -> dict[str, object]:
    """Run plan.preprocessing_steps and emit state updates for Analysis."""
    plan = state["plan"]
    if plan is None:
        warning = WarningEvent(
            code="INVALID_DATA",
            message="preprocessing node requires a validated plan",
            source=PREPROCESSING_SOURCE,
        )
        return {"warnings": [*state["warnings"], warning]}

    processed_dataset, report = run_shared_preprocessing(
        state["dataset"], plan.preprocessing_steps
    )
    return {
        "processed_dataset": processed_dataset,
        "preprocessing_report": report,
    }
