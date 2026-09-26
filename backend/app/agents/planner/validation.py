"""Validation for plans produced by the Planner Agent."""

from backend.app.contracts.models import DatasetReference, Plan, PlanStep
from backend.app.tools.registry import ToolRegistry, order_steps, validate_call


def validate_plan(
    plan: Plan,
    dataset: DatasetReference,
    registry: ToolRegistry,
) -> None:
    """Validate that a plan can be executed with the current dataset and tools."""
    _validate_required_columns(plan, dataset)
    _validate_unique_step_ids(plan)
    _validate_steps(plan.preprocessing_steps, dataset, registry)
    _validate_steps(plan.analysis_steps, dataset, registry)


def _validate_required_columns(
    plan: Plan,
    dataset: DatasetReference,
) -> None:
    missing = [
        column
        for column in plan.required_columns
        if column not in dataset.dataset_schema
    ]
    if missing:
        raise ValueError(f"Unknown required columns: {', '.join(missing)}")


def _validate_unique_step_ids(plan: Plan) -> None:
    steps = [*plan.preprocessing_steps, *plan.analysis_steps]
    step_ids = [step.step_id for step in steps]

    if len(step_ids) != len(set(step_ids)):
        raise ValueError("Duplicate step_id")


def _validate_steps(
    steps: list[PlanStep],
    dataset: DatasetReference,
    registry: ToolRegistry,
) -> None:
    order_steps(steps)

    for step in steps:
        tool = registry.get(step.tool_name)
        if tool is None:
            raise ValueError(f"Unknown tool: {step.tool_name}")

        problem = validate_call(step, dataset, tool)
        if problem is not None:
            code, message = problem
            raise ValueError(f"{code}: {message}")
