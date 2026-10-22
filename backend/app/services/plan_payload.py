"""Validate the plan and analysis payloads sent back by the browser."""

from typing import TypeVar

from pydantic import BaseModel, ValidationError

from backend.app.contracts.models import AnalysisResult, Plan

ModelT = TypeVar("ModelT", bound=BaseModel)


def load_plan(plan_payload: object) -> Plan:
    return load_model(plan_payload, Plan, "The plan is not valid")


def load_results(results_payload: object) -> list[AnalysisResult]:
    if not isinstance(results_payload, list):
        raise ValueError("The analysis results are not valid")
    try:
        return [AnalysisResult.model_validate(item) for item in results_payload]
    except ValidationError as exc:
        raise ValueError("The analysis results are not valid") from exc


def load_model(payload: object, model: type[ModelT], message: str) -> ModelT:
    if not isinstance(payload, dict):
        raise ValueError(message)
    try:
        return model.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(message) from exc
