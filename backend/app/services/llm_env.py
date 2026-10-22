"""Shared NTNU LLM settings for the hosted and local servers."""

import os

from openai import OpenAI


def ensure_llm_environment() -> None:
    if os.getenv("IDUN_API_KEY") and not os.getenv("NTNU_LLM_API_KEY"):
        os.environ["NTNU_LLM_API_KEY"] = os.environ["IDUN_API_KEY"]
    os.environ.setdefault("NTNU_LLM_BASE_URL", "https://llm.hpc.ntnu.no/v1")
    os.environ.setdefault("NTNU_LLM_MODEL", "openai/gpt-oss-120b")


def ntnu_client() -> OpenAI:
    ensure_llm_environment()
    return OpenAI(
        base_url=os.environ["NTNU_LLM_BASE_URL"],
        api_key=os.environ["NTNU_LLM_API_KEY"],
    )
