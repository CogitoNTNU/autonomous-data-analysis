"""Idun-backed generation of validated preprocessing steps."""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Any

from ...models.dataset import DatasetReference
from ...models.plan import PlanStep
from ...tools.preprocessing_tools import CANONICAL_TOOL_NAMES, resolve_dataset_path

DEFAULT_BASE_URL = "https://llm.hpc.ntnu.no/v1"
DEFAULT_MODEL = "openai/gpt-oss-120b"
PLAN_FUNCTION_NAME = "submit_preprocessing_plan"
SYSTEM_PROMPT = Path(__file__).with_name("prompt.md").read_text(encoding="utf-8")


def _plan_tool_schema() -> dict[str, Any]:
    step_schema = {
        "type": "object",
        "properties": {
            "step_id": {"type": "string"},
            "tool_name": {"type": "string", "enum": list(CANONICAL_TOOL_NAMES)},
            "arguments": {"type": "object"},
            "depends_on": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["step_id", "tool_name", "arguments"],
        "additionalProperties": False,
    }
    return {
        "type": "function",
        "function": {
            "name": PLAN_FUNCTION_NAME,
            "description": "Return registered preprocessing steps for the dataset.",
            "parameters": {
                "type": "object",
                "properties": {"steps": {"type": "array", "items": step_schema}},
                "required": ["steps"],
                "additionalProperties": False,
            },
        },
    }


def _dataset_summary(dataset: DatasetReference) -> dict[str, Any]:
    if dataset.format != "csv":
        raise ValueError("Idun preprocessing planning currently supports CSV datasets only")
    path = resolve_dataset_path(dataset.uri)
    with path.open(encoding="utf-8", newline="") as csv_file:
        fieldnames = next(csv.reader(csv_file), [])

    metadata_by_name = {column.name: column for column in dataset.metadata.columns}
    columns = []
    for name in fieldnames:
        column = {"name": name}
        metadata = metadata_by_name.get(name)
        if metadata is not None:
            column.update(
                {
                    "data_type": metadata.data_type,
                    "nullable": metadata.nullable,
                    "missing_count": metadata.missing_count,
                }
            )
        columns.append(column)
    return {
        "format": dataset.format,
        "row_count": dataset.metadata.row_count,
        "missing_value_count": dataset.metadata.missing_value_count,
        "duplicate_row_count": dataset.metadata.duplicate_row_count,
        "columns": columns,
    }


class IdunPreprocessingPlanner:
    """Ask the configured OpenAI-compatible Idun endpoint for candidate steps."""

    def __init__(
        self,
        client: Any | None = None,
        *,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self._client = client
        self._model = model or os.getenv("IDUN_MODEL", DEFAULT_MODEL)
        self._api_key = api_key
        self._base_url = base_url or os.getenv("IDUN_BASE_URL", DEFAULT_BASE_URL)

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        api_key = self._api_key or os.getenv("IDUN_API_KEY")
        if not api_key:
            raise RuntimeError("Set IDUN_API_KEY before requesting an Idun preprocessing plan")
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key, base_url=self._base_url)
        return self._client

    def plan(self, dataset: DatasetReference, request: str) -> list[PlanStep]:
        """Generate candidate steps from schema and metadata, never CSV row values."""
        if not request.strip():
            raise ValueError("A preprocessing request is required")
        response = self._get_client().chat.completions.create(
            model=self._model,
            temperature=0,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(
                        {"request": request, "dataset": _dataset_summary(dataset)}
                    ),
                },
            ],
            tools=[_plan_tool_schema()],
            tool_choice={
                "type": "function",
                "function": {"name": PLAN_FUNCTION_NAME},
            },
        )
        tool_calls = response.choices[0].message.tool_calls or []
        if len(tool_calls) != 1 or tool_calls[0].function.name != PLAN_FUNCTION_NAME:
            raise ValueError("Idun did not return a preprocessing plan")
        try:
            plan_data = json.loads(tool_calls[0].function.arguments)
        except json.JSONDecodeError as error:
            raise ValueError("Idun returned invalid plan JSON") from error
        if not isinstance(plan_data, dict) or not isinstance(plan_data.get("steps"), list):
            raise ValueError("Idun plan must contain a steps list")

        steps = [PlanStep.model_validate(step) for step in plan_data["steps"]]
        unknown_tools = sorted(
            {step.tool_name for step in steps} - set(CANONICAL_TOOL_NAMES)
        )
        if unknown_tools:
            raise ValueError(
                f"Idun proposed unregistered tools: {', '.join(unknown_tools)}"
            )
        return steps