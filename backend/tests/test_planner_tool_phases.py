import pytest

from backend.app.agents.planner.agent import run_planner
from backend.app.agents.planner.schema import PlannerOutput
from backend.app.agents.preprocessing import register_preprocessing_tools
from backend.app.contracts.models import DatasetReference, Plan, PlanStep
from backend.app.tools.analysis.descriptive import default_registry
from backend.app.tools.registry import execute_step


@pytest.mark.parametrize(
    ("preprocessing_steps", "analysis_steps", "misplaced_tool"),
    [
        (
            [],
            [PlanStep(step_id="wrong", tool_name="remove_duplicates")],
            "remove_duplicates",
        ),
        (
            [
                PlanStep(
                    step_id="wrong",
                    tool_name="descriptive_statistics",
                    arguments={"columns": ["score"]},
                )
            ],
            [],
            "descriptive_statistics",
        ),
    ],
)
def test_planner_rejects_tools_in_the_wrong_workflow_phase(
    preprocessing_steps: list[PlanStep],
    analysis_steps: list[PlanStep],
    misplaced_tool: str,
) -> None:
    dataset = DatasetReference(
        dataset_id="scores",
        version="raw-v1",
        storage_ref="unused.csv",
        schema={"score": {"datatype": "float"}},
    )
    plan = Plan(
        plan_id="wrong-phase",
        objective="Reject a misplaced tool",
        preprocessing_steps=preprocessing_steps,
        analysis_steps=analysis_steps,
    )

    response = run_planner(
        user_query="Use a tool in the wrong phase.",
        dataset=dataset,
        conversation_context=[],
        critique=None,
        registry=register_preprocessing_tools(default_registry()),
        model=lambda prompt, context: PlannerOutput(plan=plan),
    )

    assert response.status == "error"
    assert response.error is not None
    assert misplaced_tool in response.error.message
    assert "belongs in" in response.error.message


def test_analysis_executor_rejects_a_preprocessing_tool() -> None:
    dataset = DatasetReference(
        dataset_id="scores",
        version="raw-v1",
        storage_ref="unused.csv",
        schema={"score": {"datatype": "float"}},
    )
    registry = register_preprocessing_tools(default_registry())

    result = execute_step(
        PlanStep(step_id="wrong", tool_name="remove_duplicates"),
        dataset,
        registry,
    )

    assert result.values["code"] == "INVALID_DATA"
    assert result.values["status"] == "failed"
    assert "analysis phase" in result.values["error"]


def test_planner_validates_steps_against_evolved_preprocessing_schema() -> None:
    dataset = DatasetReference(
        dataset_id="dirty",
        version="raw-v1",
        storage_ref="unused.csv",
        schema={"amount": {"datatype": "string"}},
    )
    plan = Plan(
        plan_id="clean-amount",
        objective="Clean and summarize amount",
        preprocessing_steps=[
            PlanStep(
                step_id="convert",
                tool_name="change_datatypes",
                arguments={
                    "conversions": {"amount": "currency"},
                    "invalid_value_strategy": "null",
                },
            ),
            PlanStep(
                step_id="outliers",
                tool_name="handle_outliers",
                arguments={"columns": ["amount"]},
                depends_on=["convert"],
            ),
        ],
        analysis_steps=[
            PlanStep(
                step_id="summary",
                tool_name="descriptive_statistics",
                arguments={"columns": ["amount"]},
                depends_on=["outliers"],
            )
        ],
    )

    response = run_planner(
        user_query="Clean and summarize amount.",
        dataset=dataset,
        conversation_context=[],
        critique=None,
        registry=register_preprocessing_tools(default_registry()),
        model=lambda prompt, context: PlannerOutput(plan=plan),
    )

    assert response.status == "success"
    assert response.updates.plan == plan
