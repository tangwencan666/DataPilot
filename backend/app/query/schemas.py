from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.models import QueryStatus


class SQLGenerationResult(BaseModel):
    sql: str = Field(min_length=1)
    explanation: str = Field(min_length=1, max_length=1000)
    confidence: float = Field(ge=0, le=1)
    assumptions: list[str] = Field(default_factory=list, max_length=10)


class QueryCreate(BaseModel):
    question: str

    @field_validator("question")
    @classmethod
    def non_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Question cannot be empty")
        return value


class QueryResult(BaseModel):
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    truncated: bool
    execution_time_ms: float
    sql: str


class AnalysisQueryRead(BaseModel):
    id: str
    dataset_id: str
    question: str
    generated_sql: str | None
    explanation: str | None
    status: QueryStatus
    row_count: int | None
    execution_time_ms: float | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class QueryResponse(BaseModel):
    query: AnalysisQueryRead
    generation: SQLGenerationResult
    result: QueryResult


class QueryListResponse(BaseModel):
    items: list[AnalysisQueryRead]
    total: int
    page: int
    page_size: int
