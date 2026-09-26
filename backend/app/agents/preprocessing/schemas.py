"""Input and output schemas for the preprocessing agent."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, Field

from ...models.dataset import DatasetReference
from ...models.plan import PlanStep
from ...models.results import PreprocessingReport


class PreprocessingInput(BaseModel):
    """Validated input supplied to the preprocessing node."""

    dataset: DatasetReference
    steps: list[PlanStep] = Field(default_factory=list)

    @classmethod
    def from_values(
        cls,
        dataset: DatasetReference,
        steps: Sequence[PlanStep] = (),
    ) -> PreprocessingInput:
        # Normalize tuples and other sequences before Pydantic validation.
        return cls(dataset=dataset, steps=list(steps))


class PreprocessingOutput(BaseModel):
    """Validated result returned by the preprocessing node."""

    processed_dataset: DatasetReference
    report: PreprocessingReport
