"""Local durable checkpoints and per-run leases for the backend server."""

import fcntl
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import IO

from langgraph.checkpoint.sqlite import SqliteSaver


class WorkflowCheckpoints:
    def __init__(self, directory: Path) -> None:
        self.directory = directory

    @contextmanager
    def open(self) -> Iterator[SqliteSaver]:
        self.directory.mkdir(parents=True, exist_ok=True)
        with SqliteSaver.from_conn_string(
            str(self.directory / "checkpoints.sqlite")
        ) as saver:
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
