"""Dataset contracts shared across workflow stages."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ColumnMetadata(BaseModel):
    name: str
    data_type: str
    nullable: bool
    missing_count: int
    unique_count: Optional[int] = None
    example_values: list[Any] = Field(default_factory=list)


class DatasetMetadata(BaseModel):
    row_count: int
    column_count: int
    columns: list[ColumnMetadata]
    missing_value_count: int
    duplicate_row_count: int
    created_at: datetime


class DatasetReference(BaseModel):
    model_config = ConfigDict(frozen=True)

    dataset_id: str
    version: str
    uri: str
    format: Literal["csv", "parquet", "database"]
    content_hash: str
    parent_version: Optional[str] = None
    metadata: DatasetMetadata
