"""Provider-independent exceptions handled at application boundaries."""


class ModelProviderError(RuntimeError):
    """A non-transient model request failure, such as invalid credentials."""


class PlanningClarificationRequired(ValueError):
    """A valid-looking plan that cannot be executed without a user choice."""

    def __init__(self, message: str, question: str) -> None:
        super().__init__(message)
        self.question = question
