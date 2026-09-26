from unittest.mock import Mock

from pydantic import BaseModel, Field

from backend.app.agents.analysis import analysis_node
from backend.app.contracts.models import DatasetReference, Plan, PlanStep
from backend.app.contracts.state import create_initial_state
from backend.app.tools.registry import Tool, ToolRegistry


class ColumnsInput(BaseModel):
    columns: list[str] = Field(min_length=1)


def _dataset() -> DatasetReference:
    return DatasetReference(
        dataset_id="test",
        version="v1",
        storage_ref="unused.csv",
        schema={"age": {"datatype": "integer"}},
    )


def _registry(run) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        Tool(
            name="descriptive_statistics",
            description="stats",
            input_model=ColumnsInput,
            accepted_dtypes=frozenset({"integer", "float"}),
            run=run,
        )
    )
    return registry


def test_analysis_node_writes_tool_results_onto_state():
    tool = Mock(return_value={"columns": {"age": {"mean": 1.0}}, "sample_size": 3})
    state = create_initial_state("mean age", _dataset())
    state["processed_dataset"] = state["dataset"]
    state["plan"] = Plan(
        plan_id="p1",
        objective="mean age",
        analysis_steps=[
            PlanStep(
                step_id="s1",
                tool_name="descriptive_statistics",
                arguments={"columns": ["age"]},
            )
        ],
    )

    patch = analysis_node(state, registry=_registry(tool))

    assert patch["analysis_results"][0].step_id == "s1"
    assert patch["artifacts"] == []
    assert tool.call_count == 1


def test_analysis_node_warns_when_plan_is_missing():
    state = create_initial_state("mean age", _dataset())
    state["processed_dataset"] = state["dataset"]

    patch = analysis_node(state)

    assert "analysis_results" not in patch
    assert patch["warnings"][0].code == "INVALID_DATA"
    assert "plan" in patch["warnings"][0].message
