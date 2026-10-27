"""Serialize review evidence without forwarding raw execution exceptions."""

from backend.app.contracts.models import WarningEvent

from .schema import CriticContext


def serialize_context(context: CriticContext) -> str:
    safe = context.model_copy(deep=True)
    safe.warnings = [_safe_warning(warning) for warning in safe.warnings]
    if safe.preprocessing_report is not None:
        safe.preprocessing_report.warnings = [
            _safe_warning(warning) for warning in safe.preprocessing_report.warnings
        ]
    for result in safe.analysis_results:
        result.warnings = [_safe_warning(warning) for warning in result.warnings]
        if isinstance(result.values, dict) and result.values.get("status") == "failed":
            result.values = {
                "status": "failed",
                "code": result.values.get("code"),
                "retryable": result.values.get("retryable", False),
                "error": "The planned step did not complete.",
            }
    return safe.model_dump_json()


def _safe_warning(warning: WarningEvent) -> WarningEvent:
    messages = {
        "TOOL_FAILURE": "A tool failed; its output may be unavailable.",
        "TIMEOUT": "A tool exceeded its execution time limit.",
        "INVALID_DATA": "An input or planned operation failed validation.",
    }
    if warning.code not in messages:
        return warning
    return warning.model_copy(update={"message": messages[warning.code]})
