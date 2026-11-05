"""Plan-caused preprocessing failures receive one bounded Planner revision."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from backend.app.agents.interpretation.schema import InterpretationContext
from backend.app.agents.planner.schema import PlannerOutput
from backend.app.agents.preprocessing import register_preprocessing_tools
from backend.app.contracts.models import (
    Critique,
    Finding,
    Interpretation,
    Plan,
    PlanStep,
)
from backend.app.contracts.state import create_initial_state
from backend.app.graph.builder import build_graph
from backend.app.graph.limits import workflow_recursion_limit
from backend.app.graph.preprocessing_repair import ISSUE_CODE
from backend.app.storage.datasets import create_dataset_reference
from backend.app.tools.analysis.descriptive import default_registry


def _profit_plan(*, plan_id: str, convert_price: bool) -> Plan:
    preprocessing_steps = []
    dependencies = []
    required_columns = ["category", "profit"]
    if convert_price:
        preprocessing_steps = [
            PlanStep(
                step_id="convert-price",
                tool_name="change_datatypes",
                arguments={"conversions": {"unit_price": "float", "date": "date"}},
            )
        ]
        dependencies = ["convert-price"]
        required_columns.extend(["unit_price", "date"])
    return Plan(
        plan_id=plan_id,
        objective="Summarize total profit by category.",
        required_columns=required_columns,
        preprocessing_steps=preprocessing_steps,
        analysis_steps=[
            PlanStep(
                step_id="profit-by-category",
                tool_name="group_aggregate",
                arguments={
                    "group_by": ["category"],
                    "aggregations": [
                        {
                            "column": "profit",
                            "function": "sum",
                            "alias": "total_profit",
                        }
                    ],
                },
                depends_on=dependencies,
            ),
            PlanStep(
                step_id="profit-chart",
                tool_name="bar_chart",
                arguments={
                    "title": "Total Profit by Category",
                    "x": "category",
                    "y": "total_profit",
                    "source_result_id": "profit-by-category",
                },
                depends_on=["profit-by-category"],
            ),
        ],
    )


def test_dirty_profit_followup_recovers_by_replanning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("backend.app.storage.datasets.ALLOWED", (tmp_path,))
    monkeypatch.setattr(
        "backend.app.tools.analysis.files.ALLOWED_DATA_DIRECTORIES", (tmp_path,)
    )
    path = tmp_path / "sales_dirty.csv"
    path.write_text(
        "transaction_id,date,category,unit_price,profit\n"
        "TX-1,2025-01-01,Books,not_available,10.00\n"
        "TX-2,2025-01-02,Home,20.00,5.00\n",
        encoding="utf-8",
    )
    original = path.read_bytes()
    dataset = create_dataset_reference(path)
    bad_plan = _profit_plan(plan_id="copied-cleaning", convert_price=True)
    revised_plan = _profit_plan(plan_id="profit-only", convert_price=False)

    def plan(prompt: str, context) -> PlannerOutput:
        if context.critique is None:
            return PlannerOutput(plan=bad_plan)
        assert context.previous_plan == bad_plan
        assert context.critique.issues[0].code == ISSUE_CODE
        assert "unit_price" in context.critique.issues[0].description
        return PlannerOutput(plan=revised_plan)

    def interpret(prompt: str, context: InterpretationContext) -> Interpretation:
        result_id = context.evidence.results[0].result_id
        return Interpretation(
            summary="Profit was summarized by category.",
            findings=[
                Finding(
                    claim="The category totals were calculated.",
                    result_ids=[result_id],
                )
            ],
        )

    planner = Mock(side_effect=plan)
    interpretation = Mock(side_effect=interpret)
    critic = Mock(return_value=Critique(decision="approved"))
    graph = build_graph(
        register_preprocessing_tools(default_registry()),
        planner,
        interpretation_model=interpretation,
        critic_model=critic,
    )
    state = create_initial_state(
        "Give me a simple overview over the profits of all items",
        dataset,
        max_revisions=1,
    )

    result = graph.invoke(
        state,
        config={"recursion_limit": workflow_recursion_limit(state["control"])},
    )

    assert result["control"].status == "completed"
    assert result["plan"] == revised_plan
    assert result["control"].revision_count == 1
    assert result["preprocessing_report"].changes == []
    assert result["processed_dataset"].version == dataset.version
    assert result["revision_history"][0].target_agent == "planner"
    assert result["revision_history"][0].critique.issues[0].code == ISSUE_CODE
    assert result["errors"][0].step_id == "convert-price"
    assert result["errors"][0].details["column"] == "unit_price"
    assert result["critique"].decision == "approved"
    assert planner.call_count == 2
    interpretation.assert_called_once()
    critic.assert_called_once()
    assert path.read_bytes() == original
