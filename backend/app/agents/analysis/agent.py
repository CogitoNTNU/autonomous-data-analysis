"""Deterministic Analysis Agent (cogito.txt §9.3)."""

from backend.app.agents.analysis.schema import EngineResult
from backend.app.contracts.errors import AgentError
from backend.app.contracts.models import (
    AnalysisExecutionReport,
    AnalysisResult,
    AnalysisUpdates,
    Artifact,
    DatasetReference,
    PlanStep,
    PreprocessingReport,
    WarningEvent,
)
from backend.app.contracts.responses import AgentResponse
from backend.app.tools.analysis.derived import (
    VISUALIZATION_TOOL_NAMES,
    group_aggregate_schema,
)
from backend.app.tools.registry import (
    DEFAULT_TIMEOUT_SECONDS,
    ToolRegistry,
    execute_step,
    fail,
    order_steps,
)

SOURCE = "analysis"


def run_analysis(
    processed_dataset: DatasetReference,
    analysis_steps: list[PlanStep],
    preprocessing_report: PreprocessingReport | None = None,
    registry: ToolRegistry | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> EngineResult:
    if registry is None:
        from backend.app.tools.analysis.descriptive import default_registry

        registry = default_registry()
    log: list[str] = []
    if preprocessing_report is not None:
        log.append(
            f"preprocessing {preprocessing_report.rows_before}->{preprocessing_report.rows_after}"
        )
    try:
        if not analysis_steps:
            raise ValueError("Analysis requires at least one step")
        order = order_steps(analysis_steps)
    except ValueError as exc:
        warning = WarningEvent(code="INVALID_DATA", message=str(exc), source=SOURCE)
        empty = AgentResponse(
            status="error",
            updates=AnalysisUpdates(
                execution_report=AnalysisExecutionReport(outcome="failed")
            ),
            warnings=[warning],
            error=AgentError(
                code="INVALID_DATA",
                message="Analysis plan is empty or has invalid dependencies.",
                source=SOURCE,
            ),
        )
        return EngineResult(
            empty, [step.step_id for step in analysis_steps], [str(exc)]
        )
    by_id = {step.step_id: step for step in analysis_steps}
    failed: set[str] = set()
    completed: list[str] = []
    attempted_failures: list[str] = []
    results: list[AnalysisResult] = []
    warnings: list[WarningEvent] = []
    missing: list[str] = []
    cache: dict[str, AnalysisResult] = {}
    artifacts: list[Artifact] = []
    for step_id in order:
        step = by_id[step_id]
        blocked = [dep for dep in step.depends_on if dep in failed]
        if blocked:
            missing.append(step_id)
            failed.add(step_id)
            log.append(f"skipped {step_id}")
            warnings.append(
                WarningEvent(
                    code="DEPENDENCY_FAILED",
                    message=f"{step_id} skipped; failed deps: {', '.join(blocked)}",
                    source=SOURCE,
                    step_id=step_id,
                )
            )
            continue
        log.append(f"running {step_id}")
        source_problem = _source_result_problem(step, results)
        if source_problem is not None:
            item = fail(step, processed_dataset, *source_problem)
        else:
            execution_dataset, runtime_arguments = _dependency_input(
                step, results, processed_dataset
            )
            item = execute_step(
                step,
                execution_dataset,
                registry,
                cache=cache,
                timeout_seconds=timeout_seconds,
                artifacts=artifacts,
                log=log,
                runtime_arguments=runtime_arguments,
            )
        results.append(item)
        warnings.extend(item.warnings)
        if isinstance(item.values, dict) and item.values.get("status") == "failed":
            failed.add(step_id)
            attempted_failures.append(step_id)
            log.append(f"failed {step_id}")
        else:
            completed.append(step_id)
            log.append(f"ok {step_id}")
    report = AnalysisExecutionReport(
        outcome="failed"
        if not completed
        else "partial"
        if attempted_failures or missing
        else "complete",
        completed_step_ids=completed,
        failed_step_ids=attempted_failures,
        skipped_step_ids=missing,
    )
    failed_results = [item for item in results if item.step_id in attempted_failures]
    retryable = bool(failed_results) and all(
        isinstance(item.values, dict) and item.values.get("retryable") is True
        for item in failed_results
    )
    response = AgentResponse[AnalysisUpdates](
        status="error" if report.outcome == "failed" else "success",
        error=AgentError(
            code="TOOL_FAILURE",
            message="No analysis steps completed successfully; inspect the execution report and result errors.",
            source=SOURCE,
            retryable=retryable,
        )
        if report.outcome == "failed"
        else None,
        updates=AnalysisUpdates(
            analysis_results=results, artifacts=artifacts, execution_report=report
        ),
        warnings=warnings,
    )
    return EngineResult(response, missing, log)


def _source_result_problem(
    step: PlanStep, results: list[AnalysisResult]
) -> tuple[str, str] | None:
    source_result_id = step.arguments.get("source_result_id")
    if source_result_id is None or not isinstance(source_result_id, str):
        return None
    source = next(
        (
            result
            for result in results
            if result.result_id == source_result_id
            or (
                result.step_id == source_result_id and result.step_id in step.depends_on
            )
        ),
        None,
    )
    if source is None:
        return "INVALID_DATA", f"Unknown source_result_id: {source_result_id}"
    if isinstance(source.values, dict) and source.values.get("status") == "failed":
        return "DEPENDENCY_FAILED", f"Source result failed: {source_result_id}"
    return None


def _dependency_input(
    step: PlanStep,
    results: list[AnalysisResult],
    dataset: DatasetReference,
) -> tuple[DatasetReference, dict[str, object] | None]:
    if step.tool_name not in VISUALIZATION_TOOL_NAMES:
        return dataset, None
    columns = {
        column
        for name in ("x", "y", "group")
        if isinstance(column := step.arguments.get(name), str)
    }
    if columns <= set(dataset.dataset_schema):
        return dataset, None
    for dependency in step.depends_on:
        source = next(
            (result for result in results if result.step_id == dependency), None
        )
        if source is None or not isinstance(source.values, dict):
            continue
        rows = source.values.get("groups")
        if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
            continue
        schema = group_aggregate_schema(source.parameters, dataset.dataset_schema)
        if columns <= set(schema):
            derived_dataset = dataset.model_copy(update={"dataset_schema": schema})
            return derived_dataset, {
                "_source_rows": rows,
                "source_result_id": source.result_id,
            }
    return dataset, None
