"""Small datasets and injected models for complete graph tests."""

from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock

import pytest
from langgraph.graph.state import CompiledStateGraph

from backend.app.agents.interpretation.schema import InterpretationContext
from backend.app.agents.planner.schema import PlannerOutput
from backend.app.agents.preprocessing import register_preprocessing_tools
from backend.app.contracts.models import (
    Critique,
    CritiqueIssue,
    DatasetReference,
    Finding,
    Interpretation,
    Plan,
    PlanStep,
)
from backend.app.graph.builder import build_graph
from backend.app.storage.datasets import create_dataset_reference
from backend.app.tools.analysis.descriptive import default_registry
from backend.app.tools.registry import ToolRegistry


@pytest.fixture
def pipeline_dataset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> DatasetReference:
    monkeypatch.setattr("backend.app.storage.datasets.ALLOWED", (tmp_path,))
    monkeypatch.setattr(
        "backend.app.tools.analysis.files.ALLOWED_DATA_DIRECTORIES", (tmp_path,)
    )
    path = tmp_path / "ages.csv"
    path.write_text("age,score\n10,1\n,2\n30,3\n", encoding="utf-8")
    return create_dataset_reference(path)


@pytest.fixture
def pipeline_plan() -> Plan:
    return Plan(
        plan_id="describe-ages",
        objective="Describe age after removing missing ages.",
        preprocessing_steps=[
            PlanStep(
                step_id="drop-missing",
                tool_name="handle_missing_values",
                arguments={"columns": ["age"], "strategy": "drop_rows"},
            )
        ],
        analysis_steps=[
            PlanStep(
                step_id="describe-age",
                tool_name="descriptive_statistics",
                arguments={"columns": ["age"]},
                depends_on=["drop-missing"],
            )
        ],
    )


@pytest.fixture
def pipeline_registry() -> ToolRegistry:
    registry = register_preprocessing_tools(default_registry())
    descriptive = registry.get("descriptive_statistics")
    assert descriptive is not None
    registry.register(
        replace(
            descriptive,
            name="failing_statistics",
            run=Mock(side_effect=ValueError("Tool could not complete")),
        )
    )
    return registry


@pytest.fixture
def pipeline_models(pipeline_plan: Plan) -> tuple[Mock, Mock, Mock]:
    def interpret(prompt: str, context: InterpretationContext) -> Interpretation:
        return Interpretation(
            summary="Observed age summary.",
            findings=[
                Finding(
                    claim="Mean age is 20.0 across 2 observations.",
                    result_ids=[context.evidence.results[0].result_id],
                )
            ],
        )

    return (
        Mock(return_value=PlannerOutput(plan=pipeline_plan)),
        Mock(side_effect=interpret),
        Mock(return_value=Critique(decision="approved")),
    )


@pytest.fixture
def revision_critique() -> Critique:
    return Critique(
        decision="revise",
        issues=[
            CritiqueIssue(
                code="MISSING_CONTEXT",
                severity="warning",
                description="Explain that the sample contains observed ages only.",
                target_agent="interpretation",
            )
        ],
        required_changes=["Keep the sample-size limitation explicit."],
    )


@pytest.fixture
def pipeline_graph(
    pipeline_registry: ToolRegistry, pipeline_models: tuple[Mock, Mock, Mock]
) -> CompiledStateGraph:
    planner, interpretation, critic = pipeline_models
    return build_graph(
        registry=pipeline_registry,
        planner_model=planner,
        interpretation_model=interpretation,
        critic_model=critic,
    )
