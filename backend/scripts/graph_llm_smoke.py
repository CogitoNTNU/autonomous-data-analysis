"""Run the compiled LangGraph workflow against the configured NTNU LLM endpoint."""

import argparse
import os
from contextlib import ExitStack
from dataclasses import dataclass, field

from langgraph.graph.state import CompiledStateGraph
from openai import OpenAI

from backend.app.agents.critic.agent import CriticModel
from backend.app.agents.critic.llm import CriticLLM
from backend.app.agents.interpretation.context import build_context
from backend.app.agents.interpretation.evidence import prepare_evidence
from backend.app.agents.interpretation.llm import InterpretationLLM
from backend.app.agents.interpretation.node import build_interpretation_input
from backend.app.agents.interpretation.schema import (
    InterpretationContext,
    InterpretationModel,
)
from backend.app.agents.interpretation.validation import validate_interpretation
from backend.app.agents.planner.agent import PlannerModel
from backend.app.agents.planner.llm import PlannerLLM
from backend.app.agents.preprocessing import register_preprocessing_tools
from backend.app.contracts.models import Finding, Interpretation
from backend.app.contracts.state import AgentState, create_initial_state
from backend.app.core.llm_config import LLMSettings, load_llm_settings
from backend.app.graph.builder import build_graph
from backend.app.graph.limits import workflow_recursion_limit
from backend.app.storage.datasets import create_dataset_reference
from backend.app.tools.analysis.descriptive import default_registry
from backend.app.tools.dataset.inspection import inspection_registry

DEFAULT_DATASET = "tests/fixtures/clean.csv"


@dataclass
class ControlledInterpretation:
    """Inject one numerical error, then delegate revisions to the real model."""

    delegate: InterpretationModel
    column: str
    calls: int = 0
    feedback_received: bool = False

    def __call__(self, prompt: str, context: InterpretationContext) -> Interpretation:
        self.calls += 1
        claim = f"The mean {self.column} is -999999."
        if self.calls == 1:
            return Interpretation(
                summary=claim,
                findings=[
                    Finding(
                        claim=claim, result_ids=[context.evidence.results[0].result_id]
                    )
                ],
            )
        if self.calls == 2:
            previous = context.previous_interpretation
            self.feedback_received = (
                bool(context.revision_feedback)
                and previous is not None
                and previous.summary == claim
            )
        return self.delegate(prompt, context)


@dataclass
class SmokeRun:
    """Observations from the actual graph stream, without reproducing its merges."""

    state: AgentState
    path: list[str] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    exception_type: str | None = None
    controlled: bool = False
    feedback_received: bool = False


def execute_graph(graph: CompiledStateGraph, state: AgentState) -> SmokeRun:
    """Observe authoritative state snapshots and completed nodes in one invocation."""
    run = SmokeRun(state=state)
    try:
        for kind, payload in graph.stream(
            state,
            stream_mode=["updates", "values"],
            config={"recursion_limit": workflow_recursion_limit(state["control"])},
        ):
            if kind == "values":
                run.state = payload
            else:
                for node, updates in payload.items():
                    run.path.append(node)
                    print(f"Completed node: {node}", flush=True)
                    if node == "critic":
                        critique = updates.get("critique")
                        run.decisions.append(
                            critique.decision if critique is not None else "no critique"
                        )
    except Exception as error:  # noqa: BLE001 - smoke diagnostics must not expose provider bodies
        # Provider exceptions can contain credentials or response bodies.
        run.exception_type = type(error).__name__
    return run


def run_workflow(
    planner_model: PlannerModel,
    interpretation_model: InterpretationModel,
    critic_model: CriticModel,
    *,
    dataset_path: str = DEFAULT_DATASET,
    column: str = "age",
    max_revisions: int = 2,
    controlled: bool = False,
) -> SmokeRun:
    """Use the existing registry, ingestion boundary, graph, and injected models."""
    dataset = create_dataset_reference(dataset_path)
    query = (
        f"Use descriptive_statistics to report the mean, median, minimum, maximum, "
        f"and valid observation count of {column}. Use the dataset as-is; no "
        "preprocessing or other analyses are needed. Explain the calculated "
        "results and warnings without inferring units."
    )
    injected = (
        ControlledInterpretation(interpretation_model, column) if controlled else None
    )
    graph = build_graph(
        registry=register_preprocessing_tools(default_registry()),
        planner_model=planner_model,
        interpretation_model=injected if injected is not None else interpretation_model,
        critic_model=critic_model,
    )
    run = execute_graph(
        graph, create_initial_state(query, dataset, max_revisions=max_revisions)
    )
    run.controlled = controlled
    run.feedback_received = (
        injected.feedback_received if injected is not None else False
    )
    return run


def valid_interpretation(state: AgentState) -> bool:
    """Recheck the final draft and its citations using existing validation logic."""
    draft = state["interpretation"]
    if draft is None or not draft.findings:
        return False
    try:
        request = build_interpretation_input(state)
        validate_interpretation(
            draft, build_context(request, prepare_evidence(request))
        )
    except (KeyError, ValueError):
        return False
    return True


def smoke_passed(run: SmokeRun, valid_draft: bool) -> bool:
    """Require a full successful path and, when requested, an observed revision."""
    state = run.state
    critique = state["critique"]
    return (
        run.exception_type is None
        and list(dict.fromkeys(run.path))[:6]
        == [
            "start_run",
            "planner",
            "preprocessing",
            "analysis",
            "interpretation",
            "critic",
        ]
        and run.path[-1:] == ["finish_run"]
        and state["control"].status == "completed"
        and state["last_node_error"] is None
        and valid_draft
        and critique is not None
        and critique.decision == "approved"
        and (
            not run.controlled
            or (
                run.feedback_received
                and run.decisions[0] == "revise"
                and state["control"].revision_count >= 1
            )
        )
    )


def report_result(run: SmokeRun, valid_draft: bool) -> None:
    """Print observed results; never print clients, settings, or raw exceptions."""
    state = run.state
    ending = "ABORTED" if run.exception_type else "END"
    print("Completed path:", " -> ".join(["START", *run.path, ending]))
    print("Final status:", state["control"].status)
    print("Revision count:", state["control"].revision_count)
    critique = state["critique"]
    print("Critic decision:", critique.decision if critique is not None else "none")
    print("Critic decisions observed:", " -> ".join(run.decisions) or "none")
    print("Valid Interpretation:", valid_draft)
    if state["interpretation"] is not None:
        print("Interpretation summary:", state["interpretation"].summary)
    if run.controlled:
        print("Feedback reached the next Interpretation:", run.feedback_received)
    print("Errors:", len(state["errors"]))
    for error in state["errors"]:
        print(f"  {error.source}: {error.code} (retryable={error.retryable})")
    if run.exception_type:
        print("Execution exception:", run.exception_type)
    print("Smoke result:", "PASS" if smoke_passed(run, valid_draft) else "FAIL")


def _real_models(
    settings: LLMSettings, stack: ExitStack
) -> tuple[PlannerModel, InterpretationModel, CriticModel]:
    # The existing Planner and Critic constructors read these environment variables.
    os.environ.update(
        NTNU_LLM_API_KEY=settings.api_key.get_secret_value(),
        NTNU_LLM_BASE_URL=str(settings.base_url),
        NTNU_LLM_MODEL=settings.model_name,
    )
    planner = PlannerLLM(inspection_registry=inspection_registry())
    critic = CriticLLM()
    for model in (planner, critic):
        model.client = stack.enter_context(
            model.client.with_options(timeout=settings.timeout_seconds, max_retries=0)
        )
    client = stack.enter_context(
        OpenAI(
            api_key=settings.api_key.get_secret_value(),
            base_url=str(settings.base_url),
            timeout=settings.timeout_seconds,
            max_retries=0,
        )
    )
    interpretation = InterpretationLLM(
        client, settings.model_name, timeout_seconds=settings.timeout_seconds
    )
    return planner, interpretation, critic


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        default=DEFAULT_DATASET,
        help="Registered CSV location, relative to backend",
    )
    parser.add_argument("--column", default="age")
    parser.add_argument("--max-revisions", type=int, default=2)
    parser.add_argument("--controlled-revision", action="store_true")
    args = parser.parse_args(argv)
    if args.max_revisions < 0 or (args.controlled_revision and args.max_revisions < 1):
        parser.error(
            "max-revisions must be nonnegative and at least 1 for the controlled scenario"
        )
    print(
        "Scenario:",
        "CONTROLLED revision (injected first draft; real models afterward)"
        if args.controlled_revision
        else "FULLY REAL LLM (Planner, Interpretation, Critic)",
        flush=True,
    )
    try:
        settings = load_llm_settings(os.environ)
    except ValueError as error:
        print(f"Configuration error: {error}")
        return 2
    try:
        with ExitStack() as stack:
            run = run_workflow(
                *_real_models(settings, stack),
                dataset_path=args.dataset,
                column=args.column,
                max_revisions=args.max_revisions,
                controlled=args.controlled_revision,
            )
    except Exception as error:  # noqa: BLE001 - report setup failure without provider details
        print(f"Smoke setup failed ({type(error).__name__}).")
        return 1
    valid_draft = valid_interpretation(run.state)
    report_result(run, valid_draft)
    return 0 if smoke_passed(run, valid_draft) else 1


if __name__ == "__main__":
    raise SystemExit(main())
