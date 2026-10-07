"""Run one Idun interpretation request using synthetic, precomputed evidence."""

import argparse
import os
import sys

from openai import OpenAI, OpenAIError

from backend.app.agents.interpretation import InterpretationInput, run_interpretation
from backend.app.agents.interpretation.llm import InterpretationLLM
from backend.app.contracts.models import AnalysisResult, Plan, PlanStep, WarningEvent
from backend.app.core.llm_config import LLMSettings, load_llm_settings


def sample_request() -> InterpretationInput:
    """Return known statistics for the synthetic values 10, 20, and 30."""
    step = PlanStep(
        step_id="sample-step",
        tool_name="descriptive_statistics",
        arguments={"columns": ["value"]},
    )
    result = AnalysisResult(
        result_id="sample-result",
        step_id=step.step_id,
        dataset_version="synthetic-v1",
        method=step.tool_name,
        parameters=step.arguments,
        sample_size=3,
        values={
            "status": "partial",
            "columns": {
                "value": {
                    "mean": 20.0,
                    "median": 20.0,
                    "std": 10.0,
                    "min": 10.0,
                    "max": 30.0,
                    "n": 3,
                    "missing_rate": 0.0,
                }
            },
        },
        warnings=[
            WarningEvent(
                code="LOW_SAMPLE_SIZE",
                source="descriptive_statistics",
                step_id=step.step_id,
                message="value n=3",
            )
        ],
    )
    return InterpretationInput(
        run_id="idun-connection-check",
        user_query="Summarize the calculated values.",
        dataset_version="synthetic-v1",
        analysis_results=[result],
        artifacts=[],
        plan=Plan(
            plan_id="sample-plan",
            objective="Summarize the calculated values.",
            analysis_steps=[step],
            assumptions=["These are synthetic test values."],
        ),
    )


def check_connection(settings: LLMSettings) -> int:
    """Make one request; print only safe outcomes, never credentials or raw output."""
    try:
        with OpenAI(
            api_key=settings.api_key.get_secret_value(),
            base_url=str(settings.base_url),
            max_retries=0,
            timeout=settings.timeout_seconds,
        ) as client:
            model = InterpretationLLM(
                client, settings.model_name, timeout_seconds=settings.timeout_seconds
            )
            response = run_interpretation(sample_request(), model)
    except OpenAIError:
        print(
            "Provider request failed. Check your local Idun settings and NTNU network/VPN.",
            file=sys.stderr,
        )
        return 1
    if response.status != "success":
        print(
            f"Interpretation check failed ({response.error.code}): {response.error.message}",
            file=sys.stderr,
        )
        print(
            "Check your key, model, NTNU network/VPN, and the model's JSON-mode support.",
            file=sys.stderr,
        )
        return 1
    print(
        "Idun connection and interpretation contract check passed. No Critic review was performed."
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    """Load local environment settings; --check-config never contacts the provider."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="Validate local settings without a network request",
    )
    args = parser.parse_args(argv)
    try:
        settings = load_llm_settings(os.environ)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    if args.check_config:
        print("Local LLM configuration is valid. Credentials have not been tested.")
        return 0
    return check_connection(settings)


if __name__ == "__main__":
    raise SystemExit(main())
