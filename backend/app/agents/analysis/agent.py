"""Deterministic Analysis Agent (cogito.txt §9.3)."""

from backend.app.agents.analysis.schema import EngineResult
from backend.app.contracts.models import (
    AnalysisResult,
    AnalysisUpdates,
    Artifact,
    DatasetReference,
    PlanStep,
    PreprocessingReport,
    WarningEvent,
)
from backend.app.contracts.responses import AgentResponse
from backend.app.tools.registry import (
    DEFAULT_TIMEOUT_SECONDS,
    ToolRegistry,
    execute_step,
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
    from backend.app.tools.analysis.descriptive import default_registry

    active = registry or default_registry()
    log: list[str] = []
    if preprocessing_report is not None:
        log.append(
            f"preprocessing {preprocessing_report.rows_before}->{preprocessing_report.rows_after}"
        )
    try:
        order = order_steps(analysis_steps)
    except ValueError as exc:
        warning = WarningEvent(code="INVALID_DATA", message=str(exc), source=SOURCE)
        empty = AgentResponse(
            status="success", updates=AnalysisUpdates(), warnings=[warning]
        )
        return EngineResult(
            empty, [step.step_id for step in analysis_steps], [str(exc)]
        )
    by_id = {step.step_id: step for step in analysis_steps}
    failed: set[str] = set()
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
        item = execute_step(
            step,
            processed_dataset,
            active,
            cache=cache,
            timeout_seconds=timeout_seconds,
            artifacts=artifacts,
            log=log,
        )
        results.append(item)
        warnings.extend(item.warnings)
        if isinstance(item.values, dict) and item.values.get("status") == "failed":
            failed.add(step_id)
            log.append(f"failed {step_id}")
        else:
            log.append(f"ok {step_id}")
    response = AgentResponse(
        status="success",
        updates=AnalysisUpdates(analysis_results=results, artifacts=artifacts),
        warnings=warnings,
    )
    return EngineResult(response, missing, log)
