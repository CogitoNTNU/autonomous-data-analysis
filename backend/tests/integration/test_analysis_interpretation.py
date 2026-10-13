"""Real analysis results reach Interpretation through shared workflow state."""

from pathlib import Path
from unittest.mock import Mock

from backend.app.agents.analysis.node import analysis_node
from backend.app.agents.interpretation import interpretation_node
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
    state.update(analysis_node(state))
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
