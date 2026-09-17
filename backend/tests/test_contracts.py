import pytest
from pydantic import ValidationError

from backend.app.contracts import AgentError, AgentResponse, create_initial_state
from backend.app.contracts.models import (
    AnalysisResult, Critique, CriticUpdates, DatasetReference, Finding,
    Plan, PlannerUpdates, RunControl,
)


def dataset():
    return DatasetReference(
        dataset_id="penguins", version="v1", storage_ref="data/penguins.csv",
        schema={"body_mass_g": {"datatype": "integer"}},
    )


def test_runs_do_not_share_mutable_data():
    original = dataset()
    first = create_initial_state("Mean mass?", original)
    second = create_initial_state("Mean mass?", original)
    first["dataset"].dataset_schema["extra"] = "string"
    first["control"].revision_count = 1
    first["errors"].append(AgentError(code="TIMEOUT", message="Timed out", source="analysis"))
    assert first["run_id"] != second["run_id"]
    assert "extra" not in original.dataset_schema
    assert "extra" not in second["dataset"].dataset_schema
    assert second["errors"] == []
    assert second["control"].revision_count == 0
    assert second["control"].max_revisions == 2


def test_wire_schema_round_trip():
    reference = dataset()
    payload = reference.model_dump(mode="json", by_alias=True)
    assert "schema" in payload and "dataset_schema" not in payload
    assert DatasetReference.model_validate(payload) == reference


def test_planner_response_validation_and_partial_update():
    response = AgentResponse[PlannerUpdates].model_validate({
        "status": "success",
        "updates": {"plan": {"plan_id": "p1", "objective": "Mean mass"}},
    })
    assert isinstance(response.updates.plan, Plan)
    assert set(response.updates.model_dump(exclude_unset=True)) == {"plan"}
    with pytest.raises(ValidationError):
        AgentResponse[PlannerUpdates].model_validate({
            "status": "success", "updates": {"analysis_results": []},
        })


@pytest.mark.parametrize("payload", [
    {"status": "error"},
    {"status": "needs_clarification"},
    {"status": "success", "clarification_question": "Which column?"},
    {"status": "success", "error": {"code": "TIMEOUT", "message": "Timeout", "source": "planner"}},
])
def test_inconsistent_status_is_rejected(payload):
    with pytest.raises(ValidationError):
        AgentResponse[PlannerUpdates].model_validate({**payload, "updates": {}})


def test_clarification_and_error_responses():
    response = AgentResponse[PlannerUpdates](
        status="needs_clarification", updates=PlannerUpdates(),
        clarification_question="Which column?",
    )
    assert response.updates.model_dump(exclude_unset=True) == {}
    failure = AgentResponse[PlannerUpdates](
        status="error", updates=PlannerUpdates(),
        error=AgentError(code="MISSING_COLUMN", message="Unknown column", source="planner"),
    )
    assert failure.error.retryable is False


def test_critic_success_can_request_revision():
    response = AgentResponse[CriticUpdates](
        status="success",
        updates=CriticUpdates(critique=Critique(decision="revise", required_changes=["Check sample"])),
    )
    assert response.updates.critique.decision == "revise"


def test_invalid_payloads_are_rejected():
    with pytest.raises(ValidationError):
        Finding(claim="Mass increased", result_ids=[])
    with pytest.raises(ValidationError):
        RunControl(max_revisions=-1)
    with pytest.raises(ValidationError):
        AnalysisResult(
            result_id="r1", step_id="s1", dataset_version="v1",
            method="mean", values={"mean": 4}, sample_size=-1,
        )
