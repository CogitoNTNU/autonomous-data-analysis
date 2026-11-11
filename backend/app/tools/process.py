"""Cancellable process boundary for registered production analysis tools."""

import multiprocessing
from collections.abc import Callable
from multiprocessing.connection import Connection
from typing import Any

from backend.app.contracts.models import DatasetReference


def run_isolated(
    run: Callable[..., dict[str, Any]],
    dataset: DatasetReference,
    arguments: dict[str, Any],
    timeout_seconds: float,
) -> dict[str, Any]:
    """Receive before joining so a large result cannot fill a pipe and deadlock."""
    context = multiprocessing.get_context("spawn")
    receiving, sending = context.Pipe(duplex=False)
    process = context.Process(target=_run, args=(sending, run, dataset, arguments))
    try:
        process.start()
        sending.close()
        if not receiving.poll(timeout_seconds):
            raise TimeoutError("The tool exceeded its execution deadline")
        try:
            succeeded, payload = receiving.recv()
        except EOFError:
            raise ValueError("The tool process exited without a result") from None
        if not succeeded:
            if payload == "connection":
                raise ConnectionError("The tool connection is temporarily unavailable")
            if payload == "timeout":
                raise TimeoutError("The tool timed out")
            raise ValueError("The tool process failed")
        return payload
    finally:
        sending.close()
        receiving.close()
        if process.pid is not None:
            # A timed-out tool must stop before any retry starts.
            if process.is_alive():
                process.terminate()
            process.join(timeout=1)
            if process.is_alive():
                process.kill()
                process.join(timeout=1)
            process.close()


def _run(
    connection: Connection,
    run: Callable[..., dict[str, Any]],
    dataset: DatasetReference,
    arguments: dict[str, Any],
) -> None:
    with connection:
        try:
            result = run(dataset, **arguments)
        except ConnectionError:
            connection.send((False, "connection"))
        except TimeoutError:
            connection.send((False, "timeout"))
        except Exception:  # noqa: BLE001 - child failures become safe parent diagnostics
            connection.send((False, "failure"))
        else:
            connection.send((True, result))
