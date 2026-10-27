"""Run a registered CSV through the graph and print a Critic-approved interpretation."""

import argparse
import os
import sys
from contextlib import ExitStack

from openai import OpenAIError

from backend.app.agents.critic.llm import CriticLLM
from backend.app.agents.interpretation.llm import InterpretationLLM
from backend.app.agents.planner.llm import PlannerLLM
from backend.app.agents.preprocessing import register_preprocessing_tools
from backend.app.contracts.state import AgentState, create_initial_state
from backend.app.core.llm_config import load_llm_settings
from backend.app.graph.builder import build_graph
from backend.app.graph.limits import workflow_recursion_limit
from backend.app.storage.datasets import create_dataset_reference
from backend.app.tools.analysis.descriptive import TOOL
from backend.app.tools.dataset.inspection import inspection_registry
from backend.app.tools.registry import ToolRegistry


def print_outcome(state: AgentState) -> int:
    """Present only the draft, clarification, or safe failure category."""
    if state["control"].status == "needs_clarification":
        print(f"Clarification needed: {state['clarification_question']}")
        print("Run again with a more specific --prompt; resume is not implemented yet.")
        return 2
    draft = state["interpretation"]
    if (
        state["control"].status == "completed"
        and draft is not None
        and state["critique"] is not None
        and state["critique"].decision == "approved"
    ):
        print("INTERPRETATION — approved by Critic")
        print(draft.model_dump_json(indent=2))
        return 0
    error = state["last_node_error"]
    code = error.code if error else "INCOMPLETE"
    print(f"Workflow did not produce an approved result ({code}).", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        required=True,
        help="CSV under backend/data; e.g. data/penguins.csv",
    )
    parser.add_argument(
        "--prompt", required=True, help="Question about descriptive statistics"
    )
    parser.add_argument("--max-revisions", type=int, default=2)
    parser.add_argument("--max-retries", type=int, default=2)
    args = parser.parse_args(argv)
    try:
        if not args.prompt.strip():
            raise ValueError("An analysis question is required")
        dataset = create_dataset_reference(args.dataset)
        state = create_initial_state(
            args.prompt,
            dataset,
            max_revisions=args.max_revisions,
            max_retries=args.max_retries,
        )
        settings = load_llm_settings(os.environ)
    except (ValueError, OSError):
        print(
            "Check your CSV path, question, and NTNU_LLM_* settings. CSVs must be in backend/data or backend/tests/fixtures.",
            file=sys.stderr,
        )
        return 2

    # The existing Planner adapter reads settings from the process environment.
    os.environ["NTNU_LLM_API_KEY"] = settings.api_key.get_secret_value()
    os.environ["NTNU_LLM_BASE_URL"] = str(settings.base_url)
    os.environ["NTNU_LLM_MODEL"] = settings.model_name
    registry = ToolRegistry()
    registry.register(TOOL)  # Only the analysis method Interpretation supports.
    register_preprocessing_tools(registry)
    try:
        planner = PlannerLLM(inspection_registry=inspection_registry())
        with ExitStack() as stack:
            client = stack.enter_context(planner.client)
            critic = CriticLLM()
            critic_client = stack.enter_context(critic.client)
            critic_client.max_retries = 0
            critic_client.timeout = settings.timeout_seconds
            client.max_retries = 0
            client.timeout = settings.timeout_seconds
            interpretation = InterpretationLLM(
                client, settings.model_name, timeout_seconds=settings.timeout_seconds
            )
            graph = build_graph(
                registry,
                planner,
                interpretation_model=interpretation,
                critic_model=critic,
            )
            for event in graph.stream(
                state,
                config={"recursion_limit": workflow_recursion_limit(state["control"])},
                stream_mode="updates",
            ):
                for node_name, updates in event.items():
                    print(f"Completed node: {node_name}", flush=True)
                    # Mirror replacement updates for the final CLI output.
                    # LangGraph maintains its own execution state.
                    state.update(updates)
    except (OpenAIError, ValueError, OSError):
        print(
            "Workflow request failed. Check provider connectivity, configuration, and dataset validity.",
            file=sys.stderr,
        )
        return 1
    return print_outcome(state)


if __name__ == "__main__":
    raise SystemExit(main())
