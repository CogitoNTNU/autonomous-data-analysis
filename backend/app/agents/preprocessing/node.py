"""Execution logic for the preprocessing agent node."""

from __future__ import annotations

from ...models.dataset import DatasetReference
from ...models.plan import PlanStep
from ...models.results import PreprocessingChange
from ...tools.preprocessing_tools import (
    build_metadata,
    execute_preprocessing_tool,
    load_csv,
    write_csv,
)
from .idun import IdunPreprocessingPlanner
from .schemas import PreprocessingInput, PreprocessingOutput


def run_preprocessing(input_data: PreprocessingInput) -> PreprocessingOutput:
    """Execute validated preprocessing steps against a CSV dataset."""
    dataset = input_data.dataset
    if not input_data.steps:
        row_count = dataset.metadata.row_count
        return PreprocessingOutput(
            processed_dataset=dataset,
            report={
                "input_dataset_version": dataset.version,
                "output_dataset_version": dataset.version,
                "rows_before": row_count,
                "rows_after": row_count,
                "no_changes": True,
            },
        )

    if dataset.format != "csv":
        raise ValueError("Only CSV datasets are supported by the preprocessing tools")

    fieldnames, rows = load_csv(dataset.uri)
    original_row_count = len(rows)
    changes: list[PreprocessingChange] = []
    affected_columns: set[str] = set()
    warnings: list[str] = []
    made_changes = False
    for step in _order_steps(input_data.steps):
        execution = execute_preprocessing_tool(
            step.tool_name, rows, fieldnames, step.arguments
        )
        rows = execution.rows
        if execution.fieldnames is not None:
            fieldnames = execution.fieldnames
        made_changes = made_changes or (
            execution.changed
            if execution.changed is not None
            else execution.rows_affected > 0
        )
        affected_columns.update(execution.affected_columns)
        warnings.extend(execution.quality_warnings)
        changes.append(
            PreprocessingChange(
                step_id=step.step_id,
                tool_name=step.tool_name,
                description=execution.description,
                affected_columns=execution.affected_columns,
                rows_affected=execution.rows_affected,
            )
        )

    output_uri, output_hash = write_csv(dataset.uri, fieldnames, rows)
    output_version = f"preprocessed-{output_hash[:12]}"
    processed_dataset = DatasetReference(
        dataset_id=dataset.dataset_id,
        version=output_version,
        uri=output_uri,
        format=dataset.format,
        content_hash=output_hash,
        parent_version=dataset.version,
        metadata=build_metadata(fieldnames, rows),
    )
    return PreprocessingOutput(
        processed_dataset=processed_dataset,
        report={
            "input_dataset_version": dataset.version,
            "output_dataset_version": output_version,
            "changes": changes,
            "affected_columns": sorted(affected_columns),
            "rows_before": original_row_count,
            "rows_after": len(rows),
            "quality_warnings": warnings,
            "no_changes": not made_changes,
        },
    )


def _order_steps(steps: list[PlanStep]) -> list[PlanStep]:
    step_ids = [step.step_id for step in steps]
    if len(step_ids) != len(set(step_ids)):
        raise ValueError("Preprocessing step_id values must be unique")

    known_ids = set(step_ids)
    for step in steps:
        unknown_dependencies = set(step.depends_on) - known_ids
        if unknown_dependencies:
            raise ValueError(
                f"Step '{step.step_id}' has unknown dependencies: "
                f"{', '.join(sorted(unknown_dependencies))}"
            )

    pending = list(steps)
    ordered = []
    completed: set[str] = set()
    while pending:
        ready = [step for step in pending if set(step.depends_on) <= completed]
        if not ready:
            raise ValueError("Preprocessing plan contains a dependency cycle")
        for step in ready:
            ordered.append(step)
            completed.add(step.step_id)
            pending.remove(step)
    return ordered


class PreprocessingAgent:
    """Offer optional model planning and deterministic step execution."""

    def __init__(self, planner: IdunPreprocessingPlanner | None = None) -> None:
        self._planner = planner if planner is not None else IdunPreprocessingPlanner()

    def plan(self, dataset: DatasetReference, request: str) -> list[PlanStep]:
        """Ask Idun for candidate steps; inspect them before calling ``run``."""
        return self._planner.plan(dataset, request)

    def run(self, dataset, steps=()) -> PreprocessingOutput:
        # Keep the original object API while the package uses a node function.
        return run_preprocessing(PreprocessingInput.from_values(dataset, steps))
