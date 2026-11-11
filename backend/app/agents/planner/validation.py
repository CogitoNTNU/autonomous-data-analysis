"""Validation for plans produced by the Planner Agent."""

from backend.app.contracts.models import DatasetReference, Plan, PlanStep
from backend.app.core.exceptions import PlanningClarificationRequired
from backend.app.tools.analysis.derived import (
    VISUALIZATION_TOOL_NAMES,
    group_aggregate_schema,
)
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
    if not plan.preprocessing_steps and not plan.analysis_steps:
        raise ValueError(
            "Plan requires at least one executable step. Inspection metadata is "
            "planning context, not analysis evidence. Use an analysis tool for "
            "data-quality questions, or request clarification if unsupported."
        )
    _validate_required_columns(plan, dataset)
    _validate_unique_step_ids(plan)
    _validate_dependencies(plan)
    _validate_single_active_dataset(plan)
    processed_dataset = _validate_preprocessing_steps(plan, dataset, registry)
    _validate_analysis_steps(plan, processed_dataset, registry)


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


def _validate_single_active_dataset(plan: Plan) -> None:
    """Reject plans that treat linear preprocessing as branching datasets."""
    filter_step_ids = {
        step.step_id
        for step in plan.preprocessing_steps
        if step.tool_name == "filter_rows"
    }
    referenced_filters = {
        dependency
        for step in plan.analysis_steps
        for dependency in step.depends_on
        if dependency in filter_step_ids
    }
    if len(referenced_filters) > 1:
        raise PlanningClarificationRequired(
            "Analysis steps reference multiple filtered preprocessing outputs, but "
            "preprocessing produces one active dataset.",
            "This workflow can analyze one independently filtered group at a time. "
            "Which group should be analyzed first?",
        )


def _validate_analysis_steps(
    plan: Plan,
    dataset: DatasetReference,
    registry: ToolRegistry,
) -> None:
    preprocessing_ids = {step.step_id for step in plan.preprocessing_steps}
    ordered_steps = [
        step.model_copy(
            update={
                "depends_on": [
                    dependency
                    for dependency in step.depends_on
                    if dependency not in preprocessing_ids
                ]
            }
        )
        for step in plan.analysis_steps
    ]
    by_id = {step.step_id: step for step in plan.analysis_steps}
    output_schemas: dict[str, dict[str, object]] = {}
    for step_id in order_steps(ordered_steps):
        step = by_id[step_id]
        source = step.arguments.get("source_result_id")
        if source is not None and (
            source not in step.depends_on or source not in output_schemas
        ):
            raise ValueError(
                "source_result_id must reference a group_aggregate dependency step ID"
            )
        input_dataset = _analysis_input_dataset(step, dataset, output_schemas)
        _validate_step(step, input_dataset, registry, "analysis")
        if step.tool_name == "group_aggregate":
            output_schemas[step_id] = group_aggregate_schema(
                step.arguments, input_dataset.dataset_schema
            )


def _analysis_input_dataset(
    step: PlanStep,
    dataset: DatasetReference,
    output_schemas: dict[str, dict[str, object]],
) -> DatasetReference:
    if step.tool_name not in VISUALIZATION_TOOL_NAMES:
        return dataset
    columns = {
        column
        for name in ("x", "y", "group")
        if isinstance(column := step.arguments.get(name), str)
    }
    for dependency in step.depends_on:
        source = step.arguments.get("source_result_id")
        if source is not None and dependency != source:
            continue
        schema = output_schemas.get(dependency)
        if schema is not None and columns <= set(schema):
            return dataset.model_copy(update={"dataset_schema": schema})
    if step.arguments.get("source_result_id") is not None:
        raise ValueError("Chart columns are absent from the referenced aggregation")
    return dataset


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
