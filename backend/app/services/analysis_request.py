"""Run the reviewed plan's analysis steps and return public results."""

import base64
from pathlib import Path

from backend.app.agents.analysis.node import analysis_node
from backend.app.contracts.models import (
    AnalysisResult,
    Artifact,
    DatasetReference,
    WarningEvent,
)
from backend.app.contracts.state import create_initial_state
from backend.app.services.plan_payload import load_plan
from backend.app.services.preprocessing_request import prepare_dataset
from backend.app.storage.datasets import BACKEND, HOSTED_UPLOADS
from backend.app.tools.visualization.load import DEFAULT_ARTIFACTS, HOSTED_ARTIFACTS

READABLE_FIGURES = (
    DEFAULT_ARTIFACTS.resolve(),
    (BACKEND / "data").resolve(),
    HOSTED_UPLOADS.resolve(),
    HOSTED_ARTIFACTS.resolve(),
)


def analyze_plan(
    dataset: DatasetReference,
    plan_payload: object,
) -> dict[str, object]:
    plan = load_plan(plan_payload)
    processed, _report = prepare_dataset(dataset, plan)
    state = create_initial_state(plan.objective, dataset)
    state["plan"] = plan
    state["processed_dataset"] = processed
    updates = analysis_node(state)
    results = updates.get("analysis_results")
    if not isinstance(results, list):
        raise ValueError(_failure(updates))
    artifacts = _artifacts(updates.get("artifacts"))
    return {
        "status": "success",
        "results": [public_result(result) for result in results],
        "artifacts": [public_artifact(artifact) for artifact in artifacts],
        "figures": figures_for(artifacts),
        "warnings": _messages(updates.get("warnings")),
    }


def public_result(result: object) -> dict[str, object]:
    if not isinstance(result, AnalysisResult):
        raise ValueError("Analysis returned an unreadable result")
    payload = _without_paths(result.model_dump(mode="json"))
    if not isinstance(payload, dict):
        raise ValueError("Analysis returned an unreadable result")
    return payload


def public_artifact(artifact: Artifact) -> dict[str, str]:
    return {"artifact_id": artifact.artifact_id, "type": artifact.type}


def figures_for(artifacts: list[Artifact]) -> list[dict[str, str]]:
    figures: list[dict[str, str]] = []
    for artifact in artifacts:
        if artifact.type != "figure":
            continue
        image = _figure_url(artifact.storage_ref)
        if image is None:
            continue
        figures.append({"artifact_id": artifact.artifact_id, "image": image})
    return figures


def _artifacts(value: object) -> list[Artifact]:
    if not isinstance(value, list):
        return []
    return [artifact for artifact in value if isinstance(artifact, Artifact)]


def _figure_url(storage_ref: str) -> str | None:
    path = Path(storage_ref)
    if path.suffix.lower() != ".png" or not path.is_file():
        return None
    resolved = path.resolve()
    if not any(resolved.is_relative_to(root) for root in READABLE_FIGURES):
        return None
    encoded = base64.b64encode(resolved.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _without_paths(value: object) -> object:
    if isinstance(value, dict):
        return {
            key: _without_paths(item)
            for key, item in value.items()
            if key != "storage_ref"
        }
    if isinstance(value, list):
        return [_without_paths(item) for item in value]
    return value


def _messages(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    messages: list[str] = []
    for warning in value:
        if isinstance(warning, WarningEvent) and warning.message not in messages:
            messages.append(warning.message)
    return messages


def _failure(updates: dict[str, object]) -> str:
    messages = _messages(updates.get("warnings"))
    if messages:
        return messages[0]
    return "Analysis could not run"
