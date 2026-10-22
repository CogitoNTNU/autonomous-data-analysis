"""Real tool execution reaches a draft; failures stop downstream model calls."""

from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock

import pytest

from backend.app.agents.planner.schema import PlannerOutput
from backend.app.contracts.models import Finding, Interpretation, Plan, PlanStep
from backend.app.contracts.state import create_initial_state
from backend.app.graph.builder import build_graph
from backend.app.storage.datasets import create_dataset_reference
from backend.app.tools.analysis.descriptive import TOOL
from backend.app.tools.registry import ToolRegistry


@pytest.mark.parametrize(
    "scenario",
    [
        "complete",
        "partial",
        "analysis_failure",
        "preprocessing_failure",
        "invalid_draft",
    ],
)
def test_pipeline_outcomes(scenario):
    path = Path(__file__).resolve().parents[1] / "fixtures" / "clean.csv"
    original = path.read_bytes()
    dataset = create_dataset_reference(path)
    plan = Plan(
        plan_id="p",
        objective="Describe age",
        analysis_steps=[
            PlanStep(
                step_id="describe", tool_name=TOOL.name, arguments={"columns": ["age"]}
            )
        ],
    )
    registry = ToolRegistry()
    registry.register(
        TOOL
        if scenario != "analysis_failure"
        else replace(TOOL, run=Mock(side_effect=ValueError("failure")))
    )
    if scenario == "partial":
        registry.register(
            replace(
                TOOL, name="broken_stats", run=Mock(side_effect=ValueError("failure"))
            )
        )
        plan.analysis_steps.append(
            PlanStep(
                step_id="broken",
                tool_name="broken_stats",
                arguments={"columns": ["age"]},
            )
        )
    if scenario == "preprocessing_failure":
        dataset.storage_ref = str(path.with_name("does-not-exist.csv"))
    planner = Mock(return_value=PlannerOutput(plan=plan))

    def interpret(prompt, context):
        result = context.evidence.results[0]
        assert result.values["columns"]["age"]["mean"] == 20.0
        return Interpretation(
            summary="Age summary",
            findings=[
                Finding(
                    claim="Mean age is 20 across three observations.",
                    result_ids=[
                        "invented" if scenario == "invalid_draft" else result.result_id
                    ],
                )
            ],
        )

    model = Mock(side_effect=interpret)
    state = create_initial_state("Describe age", dataset)
    graph = build_graph(registry, planner, model)
    result = graph.invoke(state, config={"recursion_limit": 10})
    planner.assert_called_once()
    assert result["final_response"] is None
    assert result["critique"] is None
    assert state["plan"] is None
    assert path.read_bytes() == original
    if scenario in {"complete", "partial"}:
        assert result["control"].status == "draft_completed"
        assert result["analysis_execution_report"].outcome == scenario
        assert result["interpretation"].findings[0].result_ids == [
            result["analysis_results"][0].result_id
        ]
        assert any(
            "LOW_SAMPLE_SIZE" in text for text in result["interpretation"].limitations
        )
        if scenario == "partial":
            assert result["analysis_execution_report"].failed_step_ids == ["broken"]
            assert any(
                "broken" in text for text in result["interpretation"].limitations
            )
        model.assert_called_once()
    else:
        assert result["control"].status == "error"
        assert result["interpretation"] is None
        assert result["errors"]
        if scenario == "invalid_draft":
            model.assert_called_once()
            assert result["errors"][-1].code == "INVALID_OUTPUT"
        else:
            model.assert_not_called()
        if scenario == "preprocessing_failure":
            assert result["analysis_results"] == []
