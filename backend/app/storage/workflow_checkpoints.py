"""Local durable checkpoints and per-run leases for the backend server."""

import fcntl
import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path
from typing import IO

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

from backend.app.contracts.errors import AgentError
from backend.app.contracts.final_response import FinalResponse
from backend.app.contracts.models import (
    AnalysisExecutionReport,
    AnalysisResult,
    Artifact,
    ConversationMessage,
    Critique,
    CritiqueIssue,
    DatasetReference,
    Finding,
    Interpretation,
    Plan,
    PlanStep,
    PreprocessingReport,
    ResultReference,
    RevisionRecord,
    RunControl,
    WarningEvent,
)

# Only persisted workflow contracts may be reconstructed from checkpoints.
CHECKPOINT_TYPES = (
    DatasetReference,
    RunControl,
    AgentError,
    ConversationMessage,
    Plan,
    PlanStep,
    PreprocessingReport,
    AnalysisExecutionReport,
    AnalysisResult,
    ResultReference,
    Artifact,
    WarningEvent,
    Interpretation,
    Finding,
    Critique,
    CritiqueIssue,
    RevisionRecord,
    FinalResponse,
)


class WorkflowCheckpoints:
    def __init__(self, directory: Path) -> None:
        self.directory = directory

    @contextmanager
    def open(self) -> Iterator[SqliteSaver]:
        self.directory.mkdir(parents=True, exist_ok=True)
        serializer = JsonPlusSerializer(
            allowed_msgpack_modules=[
                (model.__module__, model.__name__) for model in CHECKPOINT_TYPES
            ],
        )
        with closing(
            sqlite3.connect(
                str(self.directory / "checkpoints.sqlite"),
                check_same_thread=False,
            )
        ) as connection:
            saver = SqliteSaver(connection, serde=serializer)
            saver.setup()
            yield saver

    def acquire(self, run_id: str) -> IO[bytes]:
        self.directory.mkdir(parents=True, exist_ok=True)
        lease = (self.directory / f"{run_id}.lock").open("ab")
        try:
            fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            lease.close()
            raise ValueError("This workflow is already running") from None
        return lease

    def running(self, run_id: str) -> bool:
        try:
            with self.acquire(run_id):
                return False
        except ValueError:
            return True
