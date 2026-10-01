from backend.app.agents.planner.node import planner_node
from backend.app.agents.planner.schema import (
    ClarificationRequest,
    PlannerOutput,
)
from backend.app.contracts.models import (
    DatasetReference,
    Plan,
    PlanStep,
)
from backend.app.contracts.state import create_initial_state
from backend.app.tools.analysis.group_aggregate import TOOL as GROUP_AGGREGATE_TOOL
from backend.app.tools.registry import ToolRegistry


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


def make_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(GROUP_AGGREGATE_TOOL)
    return registry


def make_plan() -> Plan:
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
                    "group_by": ["species"],
                    "aggregations": [
                        {
                            "column": "body_mass_g",
                            "function": "mean",
                            "alias": "average_body_mass",
                        }
                    ],
                },
                depends_on=[],
            )
        ],
        expected_outputs=["Average body mass for each penguin species"],
        assumptions=[],
    )


def test_planner_node_writes_plan_to_state_updates():
    dataset = make_dataset()
    state = create_initial_state(
        user_query="Compare average body mass across species.",
        dataset=dataset,
    )
    registry = make_registry()
    plan = make_plan()

    def fake_model(prompt, context):
        return PlannerOutput(plan=plan)

    updates = planner_node(
        state=state,
        registry=registry,
        model=fake_model,
    )

    assert updates["plan"] == plan
    assert updates["clarification_question"] is None
    assert updates["warnings"] == []


def test_planner_node_writes_clarification_to_state_updates():
    dataset = make_dataset()
    state = create_initial_state(
        user_query="Compare the groups.",
        dataset=dataset,
    )
    registry = make_registry()

    question = "Which groups and which numeric variable should be compared?"

    def fake_model(prompt, context):
        return PlannerOutput(
            clarification=ClarificationRequest(
                question=question,
            )
        )

    updates = planner_node(
        state=state,
        registry=registry,
        model=fake_model,
    )

    assert updates["clarification_question"] == question
    assert "plan" not in updates
    assert updates["warnings"] == []
