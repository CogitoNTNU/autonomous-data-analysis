"""Bound generated-output corrections separately from execution retries."""

from backend.app.contracts.errors import AgentError
from backend.app.contracts.models import RunControl


def is_output_failure(error: AgentError | None) -> bool:
    return (
        error is not None
        and error.source in {"planner", "critic"}
        and error.code == "INVALID_OUTPUT"
        and error.details.get("reason") == "model_output_invalid"
    )


def can_repair_output(error: AgentError | None, control: RunControl) -> bool:
    return (
        is_output_failure(error)
        and control.output_repair_count < control.max_output_repairs
    )


def output_feedback(error: AgentError | None) -> str | None:
    if not is_output_failure(error):
        return None
    contract = "PlannerOutput" if error.source == "planner" else "Critique"
    return (
        f"Your previous {error.source} response failed output validation. "
        f"Reason: {error.details.get('output_reason')}. "
        f"Validation types: {error.details.get('validation_types', [])}. "
        "Use the same request and evidence and return one complete JSON object "
        f"matching the supplied {contract} schema. Keep the output concise; "
        "avoid redundant steps and repeated descriptions. Do not invent evidence "
        "or change the objective or review decision merely to satisfy formatting."
    )
