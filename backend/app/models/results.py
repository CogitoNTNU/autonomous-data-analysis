"""Contracts returned by preprocessing."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from .dataset import DatasetReference


class PreprocessingChange(BaseModel):
    step_id: str
    tool_name: str
    description: str
    affected_columns: list[str] = Field(default_factory=list)
    rows_affected: Optional[int] = None


class PreprocessingReport(BaseModel):
    input_dataset_version: str
    output_dataset_version: str
    changes: list[PreprocessingChange] = Field(default_factory=list)
    affected_columns: list[str] = Field(default_factory=list)
    rows_before: int
    rows_after: int
    quality_warnings: list[str] = Field(default_factory=list)
    no_changes: bool


class PreprocessingResult(BaseModel):
    processed_dataset: DatasetReference
    report: PreprocessingReport
