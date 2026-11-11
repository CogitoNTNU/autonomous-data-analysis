"""Provider-independent exceptions handled at application boundaries."""

from typing import Literal


class ModelOutputError(ValueError):
    """A generated response failed its output contract, without raw content."""

    def __init__(
        self,
        reason: Literal[
            "invalid_json", "invalid_envelope", "incomplete_response", "empty_response"
        ],
        *,
        validation_types: list[str] | None = None,
    ) -> None:
        message = (
            "The model response did not finish normally."
            if reason == "incomplete_response"
            else f"The model response failed validation ({reason})."
        )
        super().__init__(message)
        self.reason = reason
        self.validation_types = validation_types or []


class ModelProviderError(RuntimeError):
    """A non-transient model request failure, such as invalid credentials."""


class ModelConnectionError(ConnectionError):
    """The model endpoint could not be reached, before generating a response."""


class PlanningClarificationRequired(ValueError):
    """A valid-looking plan that cannot be executed without a user choice."""

    def __init__(self, message: str, question: str) -> None:
        super().__init__(message)
        self.question = question
