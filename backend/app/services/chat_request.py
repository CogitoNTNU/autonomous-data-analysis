"""Turn the reviewed interpretation into the chat agent's final answer."""

from backend.app.agents.chat.node import run_chat
from backend.app.contracts.models import Critique, Interpretation
from backend.app.services.plan_payload import load_model


def present_answer(request: dict[str, object]) -> dict[str, object]:
    interpretation = load_model(
        request.get("interpretation"),
        Interpretation,
        "The interpretation is not valid",
    )
    critique_payload = request.get("critique")
    critique = None
    if critique_payload is not None:
        critique = load_model(critique_payload, Critique, "The critique is not valid")
    answer = run_chat(interpretation, critique)
    return {"status": "success", "answer": answer.model_dump(mode="json")}
