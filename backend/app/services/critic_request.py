"""Ask the critic to review a grounded interpretation."""

from backend.app.agents.critic.agent import CriticModel, run_critic
from backend.app.agents.critic.llm import CriticLLM
from backend.app.contracts.models import Interpretation
from backend.app.services.llm_env import ensure_llm_environment
from backend.app.services.plan_payload import load_model, load_plan, load_results


def live_critic_model() -> CriticLLM:
    ensure_llm_environment()
    return CriticLLM()


def critique_interpretation(
    request: dict[str, object],
    model: CriticModel,
) -> dict[str, object]:
    plan = load_plan(request.get("plan"))
    question = request.get("question")
    query = (
        question.strip()
        if isinstance(question, str) and question.strip()
        else plan.objective
    )
    interpretation = load_model(
        request.get("interpretation"),
        Interpretation,
        "The interpretation is not valid",
    )
    response = run_critic(
        query,
        plan,
        load_results(request.get("results")),
        interpretation,
        model,
    )
    critique = response.updates.critique
    if response.status != "success" or critique is None:
        message = response.error.message if response.error is not None else ""
        raise ValueError(message or "The critic could not review the answer")
    return {"status": "success", "critique": critique.model_dump(mode="json")}
