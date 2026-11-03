"""Serialize chat evidence without raw exceptions or private storage locations."""

from pydantic import JsonValue

from backend.app.contracts.models import AnalysisResult, ResultReference, WarningEvent

from .schema import ChatContext


def serialize_context(context: ChatContext) -> str:
    safe = context.model_copy(deep=True)
    safe.warnings = [_safe_warning(warning) for warning in safe.warnings]
    if safe.preprocessing_report is not None:
        safe.preprocessing_report.warnings = [
            _safe_warning(warning) for warning in safe.preprocessing_report.warnings
        ]
    for result in safe.analysis_results:
        result.warnings = [_safe_warning(warning) for warning in result.warnings]
        result.values = _safe_values(result)
    return safe.model_dump_json()


def _safe_values(result: AnalysisResult) -> dict[str, JsonValue]:
    if isinstance(result.values, ResultReference):
        return {"status": "stored_as_artifact"}
    if result.values.get("status") != "failed":
        return result.values
    return {
        "status": "failed",
        "code": result.values.get("code"),
        "error": "The planned step did not complete.",
    }


def _safe_warning(warning: WarningEvent) -> WarningEvent:
    messages = {
        "TOOL_FAILURE": "A tool failed; its output may be unavailable.",
        "TIMEOUT": "A tool exceeded its execution time limit.",
        "INVALID_DATA": "An input or planned operation failed validation.",
    }
    if warning.code not in messages:
        return warning
    return warning.model_copy(update={"message": messages[warning.code]})
