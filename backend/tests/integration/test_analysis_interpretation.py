"""Real analysis results reach Interpretation through shared workflow state."""

from pathlib import Path
from unittest.mock import Mock

from backend.app.agents.analysis.node import analysis_node
from backend.app.agents.interpretation import interpretation_node
from backend.app.agents.interpretation.context import serialize_context
from backend.app.contracts.models import AnalysisResult
from backend.app.contracts.models import (
    DatasetReference,
    Finding,
    Interpretation,
    Plan,
    PlanStep,
)
from backend.app.contracts.state import create_initial_state


def test_analysis_node_output_is_accepted_by_interpretation_node():
    path = Path(__file__).resolve().parents[1] / "fixtures" / "clean.csv"
    original_csv = path.read_bytes()
    dataset = DatasetReference(
        dataset_id="ages",
        version="v1",
        storage_ref=str(path),
        schema={"age": {"datatype": "integer"}},
    )
    state = create_initial_state("Describe age", dataset)
    state["processed_dataset"] = dataset.model_copy(deep=True)
    state["plan"] = Plan(
        plan_id="p1",
        objective="Describe age",
        analysis_steps=[
            PlanStep(
                step_id="s1",
                tool_name="descriptive_statistics",
                arguments={"columns": ["age"]},
            ),
        ],
    )
    # Stand in for the harness's merge; nodes themselves never call each other.
    response = analysis_node(state)
    assert response.status == "success"
    state["analysis_results"] = response.updates.analysis_results
    state["artifacts"] = response.updates.artifacts
    state["analysis_execution_report"] = response.updates.execution_report
    state["warnings"].extend(response.warnings)
    result = state["analysis_results"][0]
    model = Mock(
        return_value=Interpretation(
            summary="Observed age summary.",
            findings=[
                Finding(
                    claim="Mean age is 20.0 across 3 observations.",
                    result_ids=[result.result_id],
                ),
            ],
        )
    )

    response = interpretation_node(state, model)

    assert response.status == "success"
    context = model.call_args.args[1]
    assert context.evidence.results[0].values["columns"]["age"]["mean"] == 20.0
    assert context.evidence.results[0].sample_size == 3
    assert context.evidence.results[0].dataset_version == "v1"
    assert response.updates.interpretation.findings[0].result_ids == [result.result_id]
    assert any(
        "LOW_SAMPLE_SIZE" in text
        for text in response.updates.interpretation.limitations
    )
    assert state["interpretation"] is None
    assert path.read_bytes() == original_csv


def test_large_grouped_table_reaches_interpretation_without_losing_full_results():
    dataset = DatasetReference(
        dataset_id="ports", version="v1", storage_ref="registered.csv", schema={}
    )
    state = create_initial_state("Compare countries and show every port", dataset)
    state["processed_dataset"] = dataset
    arguments = {
        "group_by": ["port"],
        "aggregations": [
            {"column": "volume", "function": "mean", "alias": "mean_volume"}
        ],
    }
    state["plan"] = Plan(
        plan_id="ports-plan",
        objective=state["user_query"],
        analysis_steps=[
            PlanStep(step_id="ports", tool_name="group_aggregate", arguments=arguments)
        ],
    )
    state["analysis_results"] = [
        AnalysisResult(
            result_id="ports-result",
            step_id="ports",
            dataset_version="v1",
            method="group_aggregate",
            parameters=arguments,
            sample_size=573,
            values={
                "status": "ok",
                "group_count": 573,
                "group_sizes": [1] * 573,
                "groups": [
                    {
                        "port": f"Port {index}: " + "long name " * 20,
                        "mean_volume": index,
                    }
                    for index in range(573)
                ],
            },
        )
    ]
    original = state["analysis_results"][0].model_dump()
    model = Mock(
        return_value=Interpretation(
            summary="The per-port table contains 573 observed groups.",
            findings=[
                Finding(
                    claim="The first displayed port has mean volume 0.",
                    result_ids=["ports-result"],
                )
            ],
        )
    )

    response = interpretation_node(state, model)

    assert response.status == "success"
    context = model.call_args.args[1]
    serialize_context(context)
    result = context.evidence.results[0]
    assert 0 < len(result.values["groups"]) < 573
    assert len(result.values["groups"]) == len(result.values["group_sizes"])
    assert result.values["group_count"] == 573
    assert result.sample_size == 573
    assert result.table_preview.total_rows == 573
    assert result.table_preview.shown_rows == len(result.values["groups"])
    assert any(
        "preview" in text and "ports-result" in text
        for text in response.updates.interpretation.limitations
    )
    assert state["analysis_results"][0].model_dump() == original
