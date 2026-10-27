"""Run the reviewed plan's preprocessing steps and return the report."""

from backend.app.agents.preprocessing.workflow import preprocessing_node
from backend.app.contracts.models import (
    DatasetReference,
    Plan,
    PreprocessingReport,
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
    response = preprocessing_node(state)
    processed = response.updates.processed_dataset
    report = response.updates.preprocessing_report
    if response.status != "success" or processed is None or report is None:
        message = response.error.message if response.error is not None else ""
        raise ValueError(message or "Preprocessing could not run")
    return processed, report
