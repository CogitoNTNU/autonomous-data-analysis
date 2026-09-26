from pathlib import Path

from backend.app.agents.analysis import analysis_node
from backend.app.agents.planner.agent import run_planner
from backend.app.agents.planner.schema import PlannerOutput
from backend.app.agents.preprocessing import (
    preprocessing_node,
    register_preprocessing_tools,
)
from backend.app.contracts.models import DatasetReference, Plan, PlanStep
from backend.app.contracts.state import create_initial_state
from backend.app.storage.datasets import create_dataset_reference
from backend.app.tools.analysis.descriptive import default_registry
from backend.app.tools.preprocessing_tools import ChangeDatatypesArguments


def _fixture_dataset() -> tuple[Path, DatasetReference]:
    fixture = Path(__file__).resolve().parent / "fixtures" / "missing.csv"
    return fixture, create_dataset_reference(fixture)


def test_planner_preprocessing_analysis_share_workflow_contracts():
    fixture, dataset = _fixture_dataset()
    plan = Plan(
        plan_id="prep-then-analysis",
        objective="Summarize complete rows",
        required_columns=["age", "score"],
        preprocessing_steps=[
            PlanStep(
                step_id="drop_missing",
                tool_name="handle_missing_values",
                arguments={
                    "columns": ["age", "score"],
                    "strategy": "drop_rows",
                },
                depends_on=[],
            )
        ],
        analysis_steps=[
            PlanStep(
                step_id="summarize_score",
                tool_name="descriptive_statistics",
                arguments={"columns": ["score"]},
                depends_on=["drop_missing"],
            )
        ],
        expected_outputs=["Mean score after preprocessing"],
        assumptions=[],
    )
    registry = register_preprocessing_tools(default_registry())
    planner_response = run_planner(
        user_query="Summarize scores after removing incomplete rows.",
        dataset=dataset,
        conversation_context=[],
        critique=None,
        registry=registry,
        model=lambda prompt, context: PlannerOutput(plan=plan),
    )
    assert planner_response.status == "success"

    state = create_initial_state("Summarize complete rows", dataset)
    state["plan"] = planner_response.updates.plan

    updates = preprocessing_node(state)
    processed_dataset = updates["processed_dataset"]
    report = updates["preprocessing_report"]
    output_path = Path(processed_dataset.storage_ref)

    try:
        assert processed_dataset.version != dataset.version
        assert processed_dataset.dataset_id == dataset.dataset_id
        assert report.rows_before == 3
        assert report.rows_after == 1
        assert report.changes[0].startswith("drop_missing (handle_missing_values)")
        assert output_path.is_file()
        assert fixture.read_text(encoding="utf-8") == "age,score\n10,1.5\n,2.5\n30,\n"

        state.update(updates)
        analysis_updates = analysis_node(state, registry)
        result = analysis_updates["analysis_results"][0]
        assert result.dataset_version == processed_dataset.version
        assert result.sample_size == 1
        assert result.values["columns"]["score"]["mean"] == 1.5
    finally:
        output_path.unlink(missing_ok=True)


def test_preprocessing_node_passes_through_dataset_when_plan_has_no_steps():
    fixture, dataset = _fixture_dataset()
    state = create_initial_state("Summarize the raw data", dataset)
    state["plan"] = Plan(
        plan_id="analysis-only",
        objective="Summarize the raw data",
        analysis_steps=[],
    )

    updates = preprocessing_node(state)

    assert updates["processed_dataset"].storage_ref == str(fixture)
    assert updates["processed_dataset"].version == dataset.version
    assert updates["preprocessing_report"].changes == []
    assert updates["preprocessing_report"].rows_before == 3
    assert updates["preprocessing_report"].rows_after == 3


def test_change_datatypes_normalizes_datetime_to_supported_date_type():
    arguments = ChangeDatatypesArguments(
        conversions={"signup date": "datetime"}
    )

    assert arguments.conversions == {"signup date": "date"}
