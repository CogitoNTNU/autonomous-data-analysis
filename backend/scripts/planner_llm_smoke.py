"""Run a prompt through Planner, Preprocessing, and Analysis."""

from __future__ import annotations

import argparse
import os
from pprint import pprint

from backend.app.agents.analysis import analysis_node
from backend.app.agents.planner.llm import PlannerLLM
from backend.app.agents.planner.node import planner_node
from backend.app.agents.preprocessing import (
    preprocessing_node,
    register_preprocessing_tools,
)
from backend.app.contracts.state import AgentState, create_initial_state
from backend.app.storage.datasets import create_dataset_reference
from backend.app.tools.analysis.descriptive import default_registry
from backend.app.tools.dataset.inspection import inspection_registry

DEFAULT_DATASET = "data/penguins.csv"
DEFAULT_PROMPT = (
    "Remove rows where body_mass_g is missing, then calculate descriptive "
    "statistics for body_mass_g."
)
DEFAULT_BASE_URL = "https://llm.hpc.ntnu.no/v1"
DEFAULT_MODEL = "openai/gpt-oss-120b"


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    return parser.parse_args()


def _configure_planner() -> None:
    api_key = os.getenv("NTNU_LLM_API_KEY") or os.getenv("IDUN_API_KEY")
    if not api_key:
        raise RuntimeError("Set NTNU_LLM_API_KEY or IDUN_API_KEY")
    os.environ["NTNU_LLM_API_KEY"] = api_key
    os.environ.setdefault("NTNU_LLM_BASE_URL", DEFAULT_BASE_URL)
    os.environ.setdefault("NTNU_LLM_MODEL", DEFAULT_MODEL)


def _print_state(state: AgentState) -> None:
    print("\nPLAN")
    pprint(state["plan"].model_dump() if state["plan"] else None)
    print("\nPREPROCESSING REPORT")
    report = state["preprocessing_report"]
    pprint(report.model_dump() if report else None)
    print("\nANALYSIS RESULTS")
    pprint([result.model_dump() for result in state["analysis_results"]])
    if state["warnings"]:
        print("\nWARNINGS")
        pprint([warning.model_dump() for warning in state["warnings"]])


def main() -> int:
    args = _arguments()
    _configure_planner()
    dataset = create_dataset_reference(args.dataset)
    registry = register_preprocessing_tools(default_registry())
    state = create_initial_state(args.prompt, dataset)
    state.update(
        planner_node(
            state,
            registry,
            PlannerLLM(inspection_registry=inspection_registry()),
        )
    )
    if state["plan"] is None:
        if state["clarification_question"]:
            print("\nCLARIFICATION NEEDED")
            print(state["clarification_question"])
        else:
            print("\nPLANNER ERRORS")
            pprint(state["errors"])
        return 1
    state.update(preprocessing_node(state))
    state.update(analysis_node(state, registry))
    _print_state(state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
