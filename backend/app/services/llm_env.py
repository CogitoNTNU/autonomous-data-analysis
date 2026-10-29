"""Shared NTNU LLM settings for the hosted and local servers."""

import os

from openai import OpenAI

from backend.app.core.llm_config import load_llm_settings


def ensure_llm_environment() -> None:
    if os.getenv("IDUN_API_KEY") and not os.getenv("NTNU_LLM_API_KEY"):
        os.environ["NTNU_LLM_API_KEY"] = os.environ["IDUN_API_KEY"]
    os.environ.setdefault("NTNU_LLM_BASE_URL", "https://llm.hpc.ntnu.no/v1")
    os.environ.setdefault("NTNU_LLM_MODEL", "openai/gpt-oss-120b")


def ntnu_client() -> OpenAI:
    ensure_llm_environment()
    settings = load_llm_settings(os.environ)
    return OpenAI(
        base_url=str(settings.base_url),
        api_key=settings.api_key.get_secret_value(),
        timeout=settings.timeout_seconds,
        max_retries=0,
    )
