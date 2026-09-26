"""Execution logic for the preprocessing agent node."""

from __future__ import annotations

from ...models.dataset import DatasetReference
from ...models.results import PreprocessingChange
from ...tools.preprocessing import TOOLS, build_metadata, load_csv, write_csv
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
    for step in input_data.steps:
        tool = TOOLS.get(step.tool_name)
        if tool is None:
            raise ValueError(f"Unknown preprocessing tool: {step.tool_name}")
        execution = tool(rows, step.arguments)
        rows = execution.rows
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
            "no_changes": all(change.rows_affected == 0 for change in changes),
        },
    )


class PreprocessingAgent:
    """Compatibility facade for callers using the agent object interface."""

    def run(self, dataset, steps=()) -> PreprocessingOutput:
        # Keep the original object API while the package uses a node function.
        return run_preprocessing(PreprocessingInput.from_values(dataset, steps))
