"""Answer one follow-up message from the recorded analysis evidence."""

from collections.abc import Callable
from pathlib import Path

from backend.app.contracts.dialogue import ChatReply

from .schema import ChatContext

PROMPT_PATH = Path(__file__).with_name("prompt.md")

ChatModel = Callable[[str, ChatContext], ChatReply]


def reply_to_message(context: ChatContext, model: ChatModel) -> ChatReply:
    """Reject replies that cite plan, result, or artifact IDs the run never produced."""
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    reply = model(prompt, context.model_copy(deep=True))
    if not set(reply.referenced_ids) <= _known_ids(context):
        raise ValueError("The chat reply referenced unknown analysis IDs")
    return reply


def _known_ids(context: ChatContext) -> set[str]:
    ids = {result.result_id for result in context.analysis_results}
    ids |= {artifact.artifact_id for artifact in context.artifacts}
    if context.plan is not None:
        steps = [*context.plan.preprocessing_steps, *context.plan.analysis_steps]
        ids |= {context.plan.plan_id, *(step.step_id for step in steps)}
    return ids
