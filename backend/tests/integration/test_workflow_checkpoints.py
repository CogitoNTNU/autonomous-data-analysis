"""Checkpoints reconstruct only explicitly registered workflow contracts."""

import logging

from pydantic import BaseModel

from backend.app.contracts.errors import AgentError
from backend.app.contracts.final_response import FinalResponse
from backend.app.contracts.models import (
    AnalysisExecutionReport,
    AnalysisResult,
    Artifact,
    ConversationMessage,
    Critique,
    CritiqueIssue,
    Finding,
    Interpretation,
    PreprocessingReport,
    ResultReference,
    RevisionRecord,
    WarningEvent,
)
from backend.app.contracts.state import create_initial_state
from backend.app.storage.workflow_checkpoints import WorkflowCheckpoints


class UnregisteredContract(BaseModel):
    value: str


def test_round_trip_preserves_workflow_contracts_without_warnings(
    tmp_path,
    pipeline_dataset,
    pipeline_plan,
    caplog,
):
    state = create_initial_state("Compare age", pipeline_dataset)
    finding = Finding(claim="Observed age summary", result_ids=["r1"])
    critique = Critique(
        decision="revise",
        issues=[
            CritiqueIssue(
                code="MISSING_CONTEXT",
                severity="warning",
                description="Explain sample size",
                target_agent="interpretation",
            )
        ],
    )
    state.update(
        plan=pipeline_plan,
        conversation_context=[ConversationMessage(role="user", content="Compare age")],
        preprocessing_report=PreprocessingReport(rows_before=3, rows_after=2),
        analysis_execution_report=AnalysisExecutionReport(
            outcome="complete", completed_step_ids=["describe-age"]
        ),
        analysis_results=[
            AnalysisResult(
                result_id="r1",
                step_id="describe-age",
                dataset_version="v2",
                method="descriptive_statistics",
                values={"columns": {"age": {"mean": 20.0}}},
                sample_size=2,
            )
        ],
        artifacts=[
            Artifact(artifact_id="figure-1", type="figure", storage_ref="figure.png")
        ],
        interpretation=Interpretation(summary="Observed ages", findings=[finding]),
        critique=critique,
        final_response=FinalResponse(text="Observed ages", findings=[finding]),
        errors=[
            AgentError(code="INVALID_OUTPUT", source="planner", message="Invalid plan")
        ],
        warnings=[
            WarningEvent(
                code="LOW_SAMPLE_SIZE", message="Small sample", source="analysis"
            )
        ],
        revision_history=[
            RevisionRecord(
                target_agent="interpretation",
                plan_id=pipeline_plan.plan_id,
                dataset_version="v2",
                critique=critique,
            )
        ],
    )
    store = WorkflowCheckpoints(tmp_path)
    with store.open() as saver:
        encoded = saver.serde.dumps_typed(state)
    with caplog.at_level(logging.WARNING), store.open() as saver:
        restored = saver.serde.loads_typed(encoded)

    assert restored == state
    assert type(restored["dataset"]) is type(state["dataset"])
    assert type(restored["control"]) is type(state["control"])
    assert isinstance(restored["errors"][0], AgentError)
    assert isinstance(
        restored["plan"].analysis_steps[0], type(pipeline_plan.analysis_steps[0])
    )
    assert isinstance(restored["analysis_results"][0], AnalysisResult)
    assert not caplog.records


def test_unregistered_types_are_not_reconstructed(tmp_path, caplog):
    with WorkflowCheckpoints(tmp_path).open() as saver:
        encoded = saver.serde.dumps_typed(UnregisteredContract(value="test"))
        with caplog.at_level(logging.WARNING):
            restored = saver.serde.loads_typed(encoded)

    assert restored == {"value": "test"}
    assert not isinstance(restored, UnregisteredContract)
    assert "Blocked deserialization" in caplog.text


def test_standalone_result_references_are_explicitly_allowed(tmp_path, caplog):
    reference = ResultReference(storage_ref="result.json")
    with WorkflowCheckpoints(tmp_path).open() as saver:
        restored = saver.serde.loads_typed(saver.serde.dumps_typed(reference))

    assert isinstance(restored, ResultReference)
    assert restored == reference
    assert not caplog.records
