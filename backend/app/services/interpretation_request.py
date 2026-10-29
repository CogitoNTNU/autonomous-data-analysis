"""Ask the interpretation agent to explain the calculated results."""

from backend.app.agents.interpretation.llm import InterpretationLLM
from backend.app.agents.interpretation.node import interpretation_node
from backend.app.agents.interpretation.schema import InterpretationModel
from backend.app.contracts.models import Artifact, DatasetReference
from backend.app.contracts.state import create_initial_state
from backend.app.services.llm_env import ntnu_client, ensure_llm_environment
from backend.app.core.llm_config import load_llm_settings
from backend.app.services.plan_payload import load_plan, load_results
from backend.app.services.preprocessing_request import prepare_dataset


def live_interpretation_model() -> InterpretationLLM:
    from os import environ

    ensure_llm_environment()
    settings = load_llm_settings(environ)
    return InterpretationLLM(
        ntnu_client(),
        settings.model_name,
        timeout_seconds=settings.timeout_seconds,
        completion=settings.completion,
    )


def interpret_results(
    dataset: DatasetReference,
    request: dict[str, object],
    model: InterpretationModel,
) -> dict[str, object]:
    plan = load_plan(request.get("plan"))
    question = _question(request.get("question"), plan.objective)
    processed, report = prepare_dataset(dataset, plan)
    state = create_initial_state(question, dataset)
    state["plan"] = plan
    state["processed_dataset"] = processed
    state["preprocessing_report"] = report
    state["analysis_results"] = load_results(request.get("results"))
    state["artifacts"] = _artifacts(request.get("artifacts"))
    response = interpretation_node(state, model)
    interpretation = response.updates.interpretation
    if response.status != "success" or interpretation is None:
        message = response.error.message if response.error is not None else ""
        raise ValueError(message or "Interpretation could not run")
    return {
        "status": "success",
        "interpretation": interpretation.model_dump(mode="json"),
    }


def _artifacts(payload: object) -> list[Artifact]:
    if payload is None:
        return []
    if not isinstance(payload, list):
        raise ValueError("The analysis artifacts are not valid")
    artifacts: list[Artifact] = []
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("The analysis artifacts are not valid")
        artifact_id = item.get("artifact_id")
        artifact_type = item.get("type")
        if not isinstance(artifact_id, str) or artifact_type not in {"figure", "table"}:
            raise ValueError("The analysis artifacts are not valid")
        artifacts.append(
            Artifact(
                artifact_id=artifact_id,
                type=artifact_type,
                storage_ref=artifact_id,
            )
        )
    return artifacts


def _question(value: object, fallback: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return fallback
