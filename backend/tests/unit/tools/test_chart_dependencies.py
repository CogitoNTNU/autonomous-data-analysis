from dataclasses import replace
from unittest.mock import Mock

import pytest

from backend.app.agents.analysis.agent import run_analysis
from backend.app.agents.planner.validation import validate_plan
from backend.app.contracts.models import DatasetReference, Plan, PlanStep
from backend.app.tools.analysis.descriptive import default_registry
from backend.app.tools.registry import ToolRegistry


def dataset() -> DatasetReference:
    return DatasetReference(
        dataset_id="data",
        version="raw",
        storage_ref="unused.csv",
        schema={"region": {"datatype": "string"}, "age": {"datatype": "integer"}},
    )


def aggregation(step_id: str, function: str) -> PlanStep:
    return PlanStep(
        step_id=step_id,
        tool_name="group_aggregate",
        arguments={
            "group_by": ["region"],
            "aggregations": [{"column": "age", "function": function, "alias": "age"}],
        },
    )


@pytest.mark.parametrize("source,expected", [(None, 10), ("second", 20)])
def test_chart_uses_aggregate_even_when_alias_matches_raw_column(
    source: str | None, expected: int
) -> None:
    chart = PlanStep(
        step_id="chart",
        tool_name="bar_chart",
        depends_on=["first", "second"],
        arguments={
            "x": "region",
            "y": "age",
            "title": "Age by region",
            **({"source_result_id": source} if source else {}),
        },
    )
    definitions = default_registry()
    registry = ToolRegistry()
    registry.register(
        replace(
            definitions.get("group_aggregate"),
            run=Mock(
                side_effect=[
                    {"groups": [{"region": "A", "age": 10}], "sample_size": 3},
                    {"groups": [{"region": "A", "age": 20}], "sample_size": 3},
                ]
            ),
        )
    )
    render = Mock(return_value={"sample_size": 3})
    registry.register(replace(definitions.get("bar_chart"), run=render))
    steps = [aggregation("first", "mean"), aggregation("second", "max"), chart]
    validate_plan(
        Plan(plan_id="chart", objective="Compare ages", analysis_steps=steps),
        dataset(),
        registry,
    )

    response = run_analysis(dataset(), steps, registry=registry).response

    assert response.status == "success"
    assert render.call_args.kwargs["_source_rows"] == [{"region": "A", "age": expected}]
    index = 1 if source else 0
    assert (
        render.call_args.kwargs["source_result_id"]
        == response.updates.analysis_results[index].result_id
    )


def test_planner_rejects_chart_source_without_declared_dependency() -> None:
    chart = PlanStep(
        step_id="chart",
        tool_name="bar_chart",
        arguments={"x": "region", "y": "age", "source_result_id": "first"},
    )
    plan = Plan(
        plan_id="chart",
        objective="Compare ages",
        analysis_steps=[aggregation("first", "mean"), chart],
    )

    with pytest.raises(ValueError, match="group_aggregate dependency"):
        validate_plan(plan, dataset(), default_registry())


def test_chart_cannot_fall_back_to_raw_columns_for_an_explicit_source() -> None:
    reference = dataset()
    reference.dataset_schema["score"] = {"datatype": "integer"}
    chart = PlanStep(
        step_id="chart",
        tool_name="bar_chart",
        depends_on=["first"],
        arguments={"x": "region", "y": "score", "source_result_id": "first"},
    )
    steps = [aggregation("first", "mean"), chart]

    with pytest.raises(ValueError, match="absent from the referenced aggregation"):
        validate_plan(
            Plan(plan_id="chart", objective="Compare scores", analysis_steps=steps),
            reference,
            default_registry(),
        )

    registry = ToolRegistry()
    definitions = default_registry()
    registry.register(
        replace(
            definitions.get("group_aggregate"),
            run=Mock(
                return_value={
                    "groups": [{"region": "A", "age": 10}],
                    "sample_size": 3,
                }
            ),
        )
    )
    render = Mock()
    registry.register(replace(definitions.get("bar_chart"), run=render))

    response = run_analysis(reference, steps, registry=registry).response

    assert response.updates.analysis_results[-1].values["status"] == "failed"
    render.assert_not_called()
