"""Read which kinds of user input a paused workflow is waiting for."""

from langgraph.types import StateSnapshot


def interrupt_kinds(snapshot: StateSnapshot) -> set[str]:
    return {
        str(pending.value.get("kind"))
        for pending in snapshot.interrupts
        if isinstance(pending.value, dict)
    }
