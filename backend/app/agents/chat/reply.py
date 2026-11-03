"""Answer one follow-up message from the recorded analysis evidence."""

from collections.abc import Callable
from pathlib import Path

from backend.app.contracts.dialogue import ChatReply

from .references import known_ids
from .schema import ChatContext

PROMPT_PATH = Path(__file__).with_name("prompt.md")

ChatModel = Callable[[str, ChatContext], ChatReply]


def reply_to_message(context: ChatContext, model: ChatModel) -> ChatReply:
    """Reject replies that cite plan, result, or artifact IDs the run never produced."""
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    reply = model(prompt, context.model_copy(deep=True))
    if not set(reply.referenced_ids) <= known_ids(context):
        raise ValueError("The chat reply referenced unknown analysis IDs")
    return reply
