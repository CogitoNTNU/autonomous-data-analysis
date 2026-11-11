from unittest.mock import Mock

import pytest
from pydantic import BaseModel

from backend.app.agents.analysis.agent import run_analysis
from backend.app.contracts.models import DatasetReference, PlanStep
from backend.app.tools.registry import Tool, ToolRegistry


class Input(BaseModel):
    column: str


@pytest.mark.parametrize(
    "payload",
    [
        {"sample_size": -1},
        {"sample_size": True},
        {"sample_size": "3"},
        {"warnings": None},
        {"warnings": ["invalid"]},
        {"artifacts": {}},
        {"artifacts": [{"type": "figure"}]},
        {"artifacts": [12]},
        {"value": object()},
        {"value": float("inf")},
        {"value": {"nested": [float("nan")]}},
    ],
)
def test_malformed_tool_output_fails_only_its_step_and_blocks_dependents(
    payload: dict,
) -> None:
    run = Mock(side_effect=[payload, {"sample_size": 2, "value": 42}])
    registry = ToolRegistry()
    registry.register(
        Tool(
            name="summary",
            description="summary",
            input_model=Input,
            accepted_dtypes=frozenset(),
            run=run,
        )
    )
    dataset = DatasetReference(
        dataset_id="data",
        version="raw",
        storage_ref="unused.csv",
        schema={"x": {"datatype": "integer"}},
    )
    steps = [
        PlanStep(step_id="bad", tool_name="summary", arguments={"column": "x"}),
        PlanStep(
            step_id="blocked",
            tool_name="summary",
            arguments={"column": "x"},
            depends_on=["bad"],
        ),
        PlanStep(step_id="independent", tool_name="summary", arguments={"column": "x"}),
    ]

    response = run_analysis(dataset, steps, registry=registry).response

    assert response.status == "success"
    assert response.updates.execution_report.outcome == "partial"
    assert response.updates.execution_report.failed_step_ids == ["bad"]
    assert response.updates.execution_report.skipped_step_ids == ["blocked"]
    assert response.updates.execution_report.completed_step_ids == ["independent"]
    assert (
        response.updates.analysis_results[0].values["error"]
        == "Tool returned invalid output."
    )
    assert response.updates.artifacts == []
