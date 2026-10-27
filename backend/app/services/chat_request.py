"""Turn the reviewed interpretation and its charts into the final chat answer."""

from backend.app.agents.chat import ChatInput, PresentedArtifact, run_chat
from backend.app.contracts.models import Critique, Interpretation
from backend.app.services.plan_payload import load_model

_INVALID_ARTIFACTS = "The analysis artifacts are not valid"


def present_answer(request: dict[str, object]) -> dict[str, object]:
    chat_input = ChatInput(
        interpretation=load_model(
            request.get("interpretation"),
            Interpretation,
            "The interpretation is not valid",
        ),
        critique=_critique(request.get("critique")),
        figure_ids=_figure_ids(request.get("artifacts")),
    )
    answer = run_chat(chat_input)
    return {"status": "success", "answer": answer.model_dump(mode="json")}


def _critique(payload: object) -> Critique | None:
    if payload is None:
        return None
    return load_model(payload, Critique, "The critique is not valid")


def _figure_ids(payload: object) -> list[str]:
    if not isinstance(payload, list):
        raise ValueError(_INVALID_ARTIFACTS)
    artifacts = [
        load_model(item, PresentedArtifact, _INVALID_ARTIFACTS) for item in payload
    ]
    return [artifact.artifact_id for artifact in artifacts if artifact.type == "figure"]
