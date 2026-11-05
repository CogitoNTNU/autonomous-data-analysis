"""Structured failures raised by the deterministic preprocessing executor."""

from backend.app.tools.preprocessing_tools import PreprocessingToolError


class PreprocessingStepError(ValueError):
    """Attach the responsible plan step without exposing the rejected value."""

    def __init__(
        self,
        step_id: str,
        tool_name: str,
        error: PreprocessingToolError,
    ) -> None:
        super().__init__(f"Preprocessing step '{step_id}' failed: {error}")
        self.step_id = step_id
        self.tool_name = tool_name
        self.details = dict(error.details)
