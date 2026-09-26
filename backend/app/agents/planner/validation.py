"""Validation for plans produced by the Planner Agent."""

from backend.app.contracts.models import DatasetReference, Plan, PlanStep
from backend.app.tools.registry import (
    Tool,
    ToolPhase,
    ToolRegistry,
    order_steps,
    validate_call,
)


def validate_plan(
    plan: Plan,
    dataset: DatasetReference,
    registry: ToolRegistry,
) -> None:
    """Validate that a plan can be executed with the current dataset and tools."""
    _validate_required_columns(plan, dataset)
    _validate_unique_step_ids(plan)
    _validate_dependencies(plan)
    processed_dataset = _validate_preprocessing_steps(plan, dataset, registry)
    _validate_steps(plan.analysis_steps, processed_dataset, registry, "analysis")


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


def _validate_dependencies(plan: Plan) -> None:
    preprocessing_ids = {step.step_id for step in plan.preprocessing_steps}
    for step in plan.preprocessing_steps:
        unavailable = set(step.depends_on) - preprocessing_ids
        if unavailable:
            raise ValueError(
                f"Preprocessing step {step.step_id} cannot depend on: "
                f"{', '.join(sorted(unavailable))}"
            )
    order_steps([*plan.preprocessing_steps, *plan.analysis_steps])


def _validate_steps(
    steps: list[PlanStep],
    dataset: DatasetReference,
    registry: ToolRegistry,
    expected_phase: ToolPhase,
) -> None:
    for step in steps:
        _validate_step(step, dataset, registry, expected_phase)


def _validate_preprocessing_steps(
    plan: Plan,
    dataset: DatasetReference,
    registry: ToolRegistry,
) -> DatasetReference:
    current = dataset.model_copy(deep=True)
    by_id = {step.step_id: step for step in plan.preprocessing_steps}
    for step_id in order_steps(plan.preprocessing_steps):
        step = by_id[step_id]
        tool = _validate_step(step, current, registry, "preprocessing")
        if tool.update_schema is not None:
            parsed = tool.input_model.model_validate(step.arguments)
            schema = tool.update_schema(current.dataset_schema, parsed)
            current = current.model_copy(update={"dataset_schema": schema})
    return current


def _validate_step(
    step: PlanStep,
    dataset: DatasetReference,
    registry: ToolRegistry,
    expected_phase: ToolPhase,
) -> Tool:
    tool = registry.get(step.tool_name)
    if tool is None:
        raise ValueError(f"Unknown tool: {step.tool_name}")
    if tool.phase != expected_phase:
        raise ValueError(
            f"Tool {step.tool_name} belongs in {tool.phase}_steps, "
            f"not {expected_phase}_steps"
        )
    problem = validate_call(step, dataset, tool)
    if problem is not None:
        code, message = problem
        raise ValueError(f"{code}: {message}")
    return tool
