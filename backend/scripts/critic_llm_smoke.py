"""Smoke-test the Critic against the real NTNU LLM with synthetic inputs.

Run from repository root:
    uv run --project backend python backend/scripts/critic_llm_smoke.py
"""

from __future__ import annotations

import os
import sys

from backend.app.agents.critic.llm import CriticLLM
from backend.app.agents.critic.node import critic_node
from backend.app.contracts.models import (
    AnalysisResult,
    DatasetReference,
    Finding,
    Interpretation,
    Plan,
)
from backend.app.contracts.state import create_initial_state

DEFAULT_BASE_URL = "https://llm.hpc.ntnu.no/v1"
DEFAULT_MODEL = "openai/gpt-oss-120b"


def configure_llm() -> None:
    """Match the existing Planner smoke script's NTNU settings."""
    key = os.getenv("NTNU_LLM_API_KEY") or os.getenv("IDUN_API_KEY")
    if not key:
        raise RuntimeError("Set NTNU_LLM_API_KEY or IDUN_API_KEY first")

    os.environ["NTNU_LLM_API_KEY"] = key
    os.environ.setdefault("NTNU_LLM_BASE_URL", DEFAULT_BASE_URL)
    os.environ.setdefault("NTNU_LLM_MODEL", DEFAULT_MODEL)


def example_state(summary: str):
    """Create a fresh state with synthetic analysis evidence (no CSV needed)."""
    dataset = DatasetReference(
        dataset_id="synthetic_penguins",
        version="v1",
        storage_ref="synthetic://critic-smoke",
        dataset_schema={"body_mass_g": {"type": "number"}},
    )

    state = create_initial_state(
        user_query="What is the average body mass of the penguins in the dataset?",
        dataset=dataset,
    )

    state["plan"] = Plan(
        plan_id="p1",
        objective="Report the average body mass of penguins",
        required_columns=["body_mass_g"],
        expected_outputs=["Mean body mass in grams"],
    )

    state["analysis_results"] = [
        AnalysisResult(
            result_id="r1",
            step_id="s1",
            dataset_version="v1",
            method="mean",
            values={"mean_body_mass_g": 4000, "unit": "g"},
            sample_size=100,
        )
    ]

    state["interpretation"] = Interpretation(
        summary=summary,
        findings=[Finding(claim=summary, result_ids=["r1"])],
    )

    return state


def main() -> int:
    configure_llm()
    model = CriticLLM()

    cases = [
        (
            "CORRECT INTERPRETATION",
            "The average body mass is 4,000 g across the 100 penguins analyzed.",
            "approved",
        ),
        (
            "INCORRECT INTERPRETATION",
            "The average body mass is 8,000 g across the 100 penguins analyzed.",
            "revise",
        ),
    ]

    for label, summary, expected in cases:
        print(f"\n=== {label} (expected: {expected}) ===")

        state = example_state(summary)

        try:
            updates = critic_node(state, model)
        except Exception as exc:
            print(
                f"Critic call failed ({type(exc).__name__}): {exc}",
                file=sys.stderr,
            )
            return 1

        state.update(updates)

        if state["errors"]:
            print("Critic returned errors:", file=sys.stderr)
            for error in state["errors"]:
                print(error.model_dump_json(indent=2), file=sys.stderr)
            return 1

        critique = state["critique"]

        if critique is None:
            print("Critic returned no critique", file=sys.stderr)
            return 1

        print(critique.model_dump_json(indent=2))
        print(f"Decision: {critique.decision} | expected: {expected}")

        if critique.decision != expected:
            print("REVIEW: The result differs from the expected example decision.")

    print("\nSmoke test finished: both calls returned valid Critique objects.")
    print("Review the issues and required_changes above for feedback quality.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
