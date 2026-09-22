"""Validated tool registry. Planner gets definitions, never raw callables."""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
from graphlib import CycleError, TopologicalSorter
from json import dumps
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ValidationError

from backend.app.contracts.models import (
    AnalysisResult,
    Artifact,
    DatasetReference,
    PlanStep,
    WarningEvent,
)

SOURCE = "analysis"
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_RANDOM_STATE = 0
WarningCode = Literal[
    "LOW_SAMPLE_SIZE",
    "HIGH_MISSING_RATE",
    "CONSTANT_COLUMN",
    "INSUFFICIENT_DATA",
    "MISSING_COLUMN",
    "INVALID_DATA",
    "TOOL_FAILURE",
    "TIMEOUT",
    "DEPENDENCY_FAILED",
]


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    input_model: type[BaseModel]
    accepted_dtypes: frozenset[str]
    run: Callable[..., dict[str, Any]]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"duplicate tool: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "schema": t.input_model.model_json_schema(),
            }
            for t in self._tools.values()
        ]


def execute_step(
    step: PlanStep,
    dataset: DatasetReference,
    registry: ToolRegistry,
    *,
    cache: dict[str, AnalysisResult] | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    artifacts: list[Artifact] | None = None,
    log: list[str] | None = None,
) -> AnalysisResult:
    tool = registry.get(step.tool_name)
    if tool is None:
        return fail(step, dataset, "TOOL_FAILURE", f"Unknown tool: {step.tool_name}")
    problem = validate_call(step, dataset, tool)
    if problem:
        return fail(step, dataset, *problem)
    key = cache_key(step, dataset)
    if cache is not None and key in cache:
        if log is not None:
            log.append(f"cache {step.step_id}")
        cached = cache[key]
        return cached.model_copy(
            update={"result_id": str(uuid4()), "step_id": step.step_id}
        )
    kwargs = dict(step.arguments)
    kwargs.setdefault("random_state", DEFAULT_RANDOM_STATE)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            payload = dict(
                pool.submit(tool.run, dataset, **kwargs).result(timeout=timeout_seconds)
            )
    except FuturesTimeoutError:
        return fail(
            step,
            dataset,
            "TIMEOUT",
            f"Tool {step.tool_name} exceeded the {timeout_seconds:.1f}s step budget",
        )
    except Exception as exc:
        return fail(step, dataset, "TOOL_FAILURE", str(exc) or type(exc).__name__)
    raw_artifacts = payload.pop("artifacts", [])
    if artifacts is not None:
        artifacts.extend(parse_artifacts(raw_artifacts))
    raw_warnings = payload.pop("warnings", [])
    sample = payload.pop("sample_size", 0)
    warnings = [as_warning(item, step.step_id) for item in raw_warnings]
    outcome = result(
        step,
        dataset,
        payload,
        sample if isinstance(sample, int) and sample >= 0 else 0,
        warnings,
    )
    if cache is not None:
        cache[key] = outcome
    return outcome


def validate_call(
    step: PlanStep, dataset: DatasetReference, tool: Tool
) -> tuple[str, str] | None:
    try:
        parsed = tool.input_model.model_validate(step.arguments)
    except ValidationError as exc:
        return "INVALID_DATA", str(exc)
    for column in getattr(parsed, "columns", []):
        info = dataset.dataset_schema.get(column)
        if not isinstance(info, dict):
            return "MISSING_COLUMN", f"Unknown column: {column}"
        if info.get("datatype") not in tool.accepted_dtypes:
            allowed = ", ".join(sorted(tool.accepted_dtypes))
            return (
                "INVALID_DATA",
                f"{column} has dtype {info.get('datatype')}; accepted: {allowed}",
            )
    return None


def order_steps(steps: list[PlanStep]) -> list[str]:
    ids = [step.step_id for step in steps]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate step_id")
    graph = {step.step_id: set(step.depends_on) for step in steps}
    extra = {dep for deps in graph.values() for dep in deps} - set(graph)
    if extra:
        raise ValueError(f"Unknown depends_on: {', '.join(sorted(extra))}")
    try:
        return list(TopologicalSorter(graph).static_order())
    except CycleError as exc:
        raise ValueError("Cyclic depends_on") from exc


def cache_key(step: PlanStep, dataset: DatasetReference) -> str:
    parameters = {
        **dict(step.arguments),
        "random_state": step.arguments.get("random_state", DEFAULT_RANDOM_STATE),
    }
    return dumps(
        {
            "method": step.tool_name,
            "parameters": parameters,
            "dataset_version": dataset.version,
        },
        sort_keys=True,
        default=str,
    )


def parse_artifacts(raw: object) -> list[Artifact]:
    if not isinstance(raw, list):
        return []
    parsed: list[Artifact] = []
    for item in raw:
        if isinstance(item, Artifact):
            parsed.append(item)
        elif isinstance(item, dict):
            parsed.append(Artifact.model_validate(item))
    return parsed


def fail(
    step: PlanStep, dataset: DatasetReference, code: WarningCode, message: str
) -> AnalysisResult:
    warning = WarningEvent(
        code=code, message=message, source=SOURCE, step_id=step.step_id
    )
    return result(step, dataset, {"error": message, "code": code}, 0, [warning])


def result(
    step: PlanStep,
    dataset: DatasetReference,
    values: dict[str, Any],
    sample_size: int,
    warnings: list[WarningEvent],
) -> AnalysisResult:
    status: Literal["ok", "partial", "failed"] = "ok"
    if values.get("error"):
        status = "failed"
    elif warnings:
        status = "partial"
    return AnalysisResult(
        result_id=str(uuid4()),
        step_id=step.step_id,
        dataset_version=dataset.version,
        method=step.tool_name,
        parameters=dict(step.arguments),
        values={**values, "status": status},
        sample_size=sample_size,
        warnings=warnings,
    )


def as_warning(item: object, step_id: str) -> WarningEvent:
    if isinstance(item, WarningEvent):
        return item.model_copy(update={"step_id": item.step_id or step_id})
    data = item if isinstance(item, dict) else {}
    return WarningEvent(
        code=str(data.get("code", "TOOL_FAILURE")),
        message=str(data.get("message", "tool warning")),
        source=str(data.get("source", SOURCE)),
        step_id=step_id,
    )
