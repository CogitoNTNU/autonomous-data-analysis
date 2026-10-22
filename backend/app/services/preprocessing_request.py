"""Run the reviewed plan's preprocessing steps and return the report."""

from backend.app.agents.preprocessing.workflow import preprocessing_node
from backend.app.contracts.models import (
    DatasetReference,
    Plan,
    PreprocessingReport,
    WarningEvent,
)
from backend.app.contracts.state import create_initial_state
from backend.app.services.plan_payload import load_plan


def preprocess_plan(
    dataset: DatasetReference,
    plan_payload: object,
) -> dict[str, object]:
    _, report = prepare_dataset(dataset, load_plan(plan_payload))
    return {"status": "success", "report": report.model_dump(mode="json")}


def prepare_dataset(
    dataset: DatasetReference,
    plan: Plan,
) -> tuple[DatasetReference, PreprocessingReport]:
    state = create_initial_state(plan.objective, dataset)
    state["plan"] = plan
    updates = preprocessing_node(state)
    processed = updates.get("processed_dataset")
    report = updates.get("preprocessing_report")
    if not isinstance(processed, DatasetReference) or not isinstance(
        report, PreprocessingReport
    ):
        raise ValueError(_failure(updates))
    return processed, report


def _failure(updates: dict[str, object]) -> str:
    warnings = updates.get("warnings")
    if isinstance(warnings, list):
        for warning in warnings:
            if isinstance(warning, WarningEvent) and warning.message:
                return warning.message
    return "Preprocessing could not run"
