from backend.app.agents.planner.agent import run_planner
from backend.app.agents.planner.schema import PlannerOutput
from backend.app.contracts.models import (
    DatasetReference,
    Plan,
    PlanStep,
)
from backend.app.tools.registry import ToolRegistry
from pydantic import BaseModel


def make_dataset() -> DatasetReference:
    return DatasetReference(
        dataset_id="penguins",
        version="1",
        storage_ref="data/penguins.csv",
        schema={
            "species": {"datatype": "string"},
            "body_mass_g": {"datatype": "float"},
        },
    )


def make_valid_plan() -> Plan:
    return Plan(
        plan_id="plan-1",
        objective="Compare average body mass across penguin species.",
        required_columns=["species", "body_mass_g"],
        preprocessing_steps=[],
        analysis_steps=[
            PlanStep(
                step_id="step-1",
                tool_name="group_aggregate",
                arguments={
                    "columns": ["body_mass_g"],
                    "group_by": ["species"],
                },
                depends_on=[],
            )
        ],
        expected_outputs=["Average body mass for each species"],
        assumptions=[],
    )


def make_registry() -> ToolRegistry:
    registry = ToolRegistry()

    class GroupAggregateInput(BaseModel):
        columns: list[str]
        group_by: list[str]

    from backend.app.tools.registry import Tool

    registry.register(
        Tool(
            name="group_aggregate",
            description="Aggregate numeric columns by groups.",
            input_model=GroupAggregateInput,
            accepted_dtypes=frozenset({"float", "integer"}),
            run=lambda dataset, **kwargs: {},
        )
    )

    return registry


def test_planner_accepts_valid_plan():
    dataset = make_dataset()
    registry = make_registry()
    plan = make_valid_plan()

    def fake_model(prompt, context):
        return PlannerOutput(plan=plan)

    response = run_planner(
        user_query=(
            "Before creating the analysis plan, inspect the body_mass_g column "
            "using the column_profile tool. Then create a plan for descriptive "
            "statistics. Include the observed minimum and maximum from the "
            "inspection in the plan assumptions."
        ),
        dataset=dataset,
        conversation_context=[],
        critique=None,
        registry=registry,
        model=fake_model,
    )

    assert response.status == "success"
    assert response.updates.plan == plan


def test_planner_rejects_invalid_plan():
    dataset = make_dataset()
    registry = make_registry()

    invalid_plan = Plan(
        plan_id="plan-2",
        objective="Compare penguins.",
        required_columns=["species", "does_not_exist"],
        preprocessing_steps=[],
        analysis_steps=[],
        expected_outputs=[],
        assumptions=[],
    )

    def fake_model(prompt, context):
        return PlannerOutput(plan=invalid_plan)

    response = run_planner(
        user_query="Compare penguins.",
        dataset=dataset,
        conversation_context=[],
        critique=None,
        registry=registry,
        model=fake_model,
    )

    assert response.status == "error"
    assert response.error is not None
    assert response.error.code == "INVALID_OUTPUT"
