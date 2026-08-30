from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models import DatasetStatus


class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str


class ColumnInfo(BaseModel):
    name: str
    dtype: str
    missing: int
    unique: int


class DatasetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    original_filename: str
    stored_filename: str
    file_type: str
    file_size: int
    row_count: int
    column_count: int
    status: DatasetStatus
    created_at: datetime
    updated_at: datetime
    metadata_json: dict[str, Any]


class DatasetListResponse(BaseModel):
    items: list[DatasetRead]
    total: int
    page: int
    page_size: int


class DatasetPreview(BaseModel):
    dataset_id: str
    filename: str
    row_count: int
    column_count: int
    columns: list[ColumnInfo]
    preview_rows: list[dict[str, Any]]
    preview_limit: int = Field(ge=1)


class ErrorResponse(BaseModel):
    detail: str
