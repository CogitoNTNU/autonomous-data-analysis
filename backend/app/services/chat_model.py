"""Create the live Chat model for follow-up messages."""

from backend.app.agents.chat.llm import ChatLLM
from backend.app.services.llm_env import ensure_llm_environment


def live_chat_model() -> ChatLLM:
    ensure_llm_environment()
    return ChatLLM()
