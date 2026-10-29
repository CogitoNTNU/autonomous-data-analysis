"""Run the harness in background workers and expose persisted snapshots."""

import logging
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack, contextmanager
from functools import cache
from typing import IO, TypeVar
from uuid import UUID

from langchain_core.runnables import RunnableConfig
from langgraph.graph import START
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command

from backend.app.agents.critic.agent import CriticModel
from backend.app.agents.interpretation.schema import InterpretationModel
from backend.app.agents.planner.agent import PlannerModel
from backend.app.contracts.errors import AgentError
from backend.app.contracts.models import DatasetReference
from backend.app.contracts.state import AgentState, create_initial_state
from backend.app.contracts.workflow import ResumeWorkflow, WorkflowSnapshot
from backend.app.graph.builder import build_graph
from backend.app.graph.limits import workflow_recursion_limit
from backend.app.services.workflow_snapshot import workflow_snapshot
from backend.app.storage.workflow_checkpoints import WorkflowCheckpoints
from backend.app.tools.registry import ToolRegistry


class WorkflowService:
    def __init__(
        self,
        store: WorkflowCheckpoints,
        registry: ToolRegistry,
        planner: Callable[[], PlannerModel],
        interpretation: Callable[[], InterpretationModel],
        critic: Callable[[], CriticModel],
    ) -> None:
        self.store, self.registry = store, registry
        self.planner, self.interpretation, self.critic = planner, interpretation, critic
        self.workers = ThreadPoolExecutor(max_workers=4, thread_name_prefix="workflow")

    @contextmanager
    def graph(self) -> Iterator[CompiledStateGraph]:
        with self.store.open() as saver, ExitStack() as resources:
            planner = _lazy_model(self.planner, resources)
            interpretation = _lazy_model(self.interpretation, resources)
            critic = _lazy_model(self.critic, resources)
            yield build_graph(
                self.registry,
                lambda prompt, context: planner()(prompt, context),
                interpretation_model=lambda prompt, context: interpretation()(
                    prompt, context
                ),
                critic_model=lambda prompt, context: critic()(prompt, context),
                checkpointer=saver,
                conversational=True,
            )

    def start(self, dataset: DatasetReference, question: str) -> WorkflowSnapshot:
        state = create_initial_state(question, dataset, max_retries=1)
        run_id = state["run_id"]
        lease = self.store.acquire(run_id)
        try:
            with self.graph() as graph:
                graph.update_state(_config(run_id), state, as_node=START)
            self.workers.submit(self._run, run_id, None, lease)
        except Exception:
            lease.close()
            raise
        return self.status(UUID(run_id))

    def status(self, run_id: UUID) -> WorkflowSnapshot:
        running = self.store.running(str(run_id))
        with self.graph() as graph:
            snapshot = graph.get_state(_config(str(run_id)))
        return workflow_snapshot(snapshot, running=running)

    def resume(self, request: ResumeWorkflow) -> WorkflowSnapshot:
        run_id = str(request.run_id)
        lease = self.store.acquire(run_id)
        try:
            with self.graph() as graph:
                snapshot = graph.get_state(_config(run_id))
            if not snapshot.values:
                raise ValueError("Unknown workflow")
            if (
                snapshot.config["configurable"]["checkpoint_id"]
                != request.checkpoint_id
            ):
                raise ValueError(
                    "The workflow has changed. Refresh its status before replying."
                )
            if not snapshot.interrupts or not snapshot.values["clarification_question"]:
                raise ValueError("This workflow is not waiting for clarification")
            self.workers.submit(
                self._run, run_id, Command(resume={"answer": request.answer}), lease
            )
        except Exception:
            lease.close()
            raise
        return self.status(request.run_id)

    def _run(self, run_id: str, command: Command | None, lease: IO[bytes]) -> None:
        with lease, self.graph() as graph:
            config = _config(run_id)
            snapshot = graph.get_state(config)
            config["recursion_limit"] = (
                workflow_recursion_limit(snapshot.values["control"]) + 10
            )
            try:
                graph.invoke(command, config=config)
            except Exception:  # noqa: BLE001 - persist a safe terminal outcome at the worker boundary
                logging.getLogger(__name__).error(
                    "workflow.failed", extra={"run_id": run_id}
                )
                state: AgentState = graph.get_state(config).values
                error = AgentError(
                    code="TOOL_FAILURE",
                    message="The workflow could not finish. Check the backend configuration and try again.",
                    source="harness",
                )
                graph.update_state(
                    config,
                    {
                        "last_node_error": error,
                        "last_node_status": "error",
                        "final_response": None,
                        "errors": [*state["errors"], error],
                        "control": state["control"].model_copy(
                            update={"status": "error", "current_agent": None}
                        ),
                    },
                    as_node="finish_run",
                )

    def close(self) -> None:
        self.workers.shutdown(wait=True)


def _config(run_id: str) -> RunnableConfig:
    return {"configurable": {"thread_id": run_id}}


ModelT = TypeVar("ModelT")


def _lazy_model(
    factory: Callable[[], ModelT], resources: ExitStack
) -> Callable[[], ModelT]:
    """Reuse each provider connection within a run; status reads create no clients."""

    @cache
    def load() -> ModelT:
        model = factory()
        close = getattr(model, "close", None)
        if callable(close):
            resources.callback(close)
        return model

    return load
