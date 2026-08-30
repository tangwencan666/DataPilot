from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models import DatasetStatus, ProfileStatus
from app.profiling.types import ProfileResult


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
    code: str = "BAD_REQUEST"
    request_id: str | None = None


class DatasetProfileRead(BaseModel):
    id: str
    dataset_id: str
    status: ProfileStatus
    profile_version: int
    row_count: int
    column_count: int
    duplicate_row_count: int
    duplicate_row_ratio: float
    missing_cell_count: int
    missing_cell_ratio: float
    quality_score: float
    generated_at: datetime | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    profile: ProfileResult | None
