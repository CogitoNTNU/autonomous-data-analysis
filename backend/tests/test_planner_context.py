import json

from pydantic import BaseModel

from backend.app.agents.planner.agent import PlannerContext
from backend.app.agents.planner.context import context_message
from backend.app.contracts.models import DatasetReference
from backend.app.tools.registry import Tool, ToolRegistry


class PreviewInput(BaseModel):
    columns: list[str] | None = None
    limit: int


def _context(query: str) -> PlannerContext:
    dataset = DatasetReference(
        dataset_id="dirty",
        version="raw-v1",
        storage_ref="unused.csv",
        schema={"email": {"datatype": "string"}},
    )
    return PlannerContext(query, dataset, [], None, [])


def test_cleaning_context_includes_representative_rows() -> None:
    registry = ToolRegistry()
    registry.register(
        Tool(
            name="preview_data",
            description="preview",
            input_model=PreviewInput,
            accepted_dtypes=frozenset(),
            run=lambda dataset, **kwargs: {
                "rows": [{"email": " USER@example.com "}],
                "returned_rows": 1,
            },
            phase="inspection",
        )
    )

    payload = json.loads(context_message(_context("Clean the data"), registry))

    assert payload["dataset_preview"]["rows"] == [
        {"email": " USER@example.com "}
    ]


def test_non_cleaning_context_does_not_read_preview() -> None:
    payload = json.loads(context_message(_context("Calculate the mean"), ToolRegistry()))

    assert "dataset_preview" not in payload
