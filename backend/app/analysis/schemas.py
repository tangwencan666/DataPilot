from datetime import datetime
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Field

from app.models import AnalysisRunStatus


class SortSpec(BaseModel):
    column: str
    direction: Literal["asc", "desc"] = "asc"


class FilterCondition(BaseModel):
    column: str
    operator: Literal["eq", "ne", "gt", "gte", "lt", "lte", "in", "not_in", "contains", "starts_with", "ends_with", "is_null", "not_null"]
    value: Any = None


class MetricSpec(BaseModel):
    column: str
    aggregation: Literal["sum", "mean", "median", "min", "max", "count", "nunique", "std"]


class Operand(BaseModel):
    type: Literal["column", "constant"]
    value: str | float | int


class SummarizeOperation(BaseModel):
    type: Literal["summarize"]
    columns: list[str] | None = None


class GroupByOperation(BaseModel):
    type: Literal["groupby_aggregate"]
    group_by: list[str]
    metrics: list[MetricSpec]
    sort: list[SortSpec] = Field(default_factory=list)
    limit: int | None = Field(default=None, ge=1)


class FilterOperation(BaseModel):
    type: Literal["filter_rows"]
    conditions: list[FilterCondition] = Field(min_length=1)


class SortOperation(BaseModel):
    type: Literal["sort_rows"]
    sort: list[SortSpec] = Field(min_length=1)


class CorrelationOperation(BaseModel):
    type: Literal["correlation"]
    columns: list[str]
    method: Literal["pearson", "spearman"] = "pearson"


class ValueCountsOperation(BaseModel):
    type: Literal["value_counts"]
    column: str
    top_n: int = Field(default=10, ge=1)
    dropna: bool = True


class DescriptiveOperation(BaseModel):
    type: Literal["descriptive_statistics"]
    columns: list[str] | None = None


class TimeSeriesOperation(BaseModel):
    type: Literal["time_series_aggregate"]
    datetime_column: str
    frequency: Literal["day", "week", "month", "quarter", "year"]
    metric: MetricSpec
    group_by: list[str] = Field(default_factory=list)


class DeriveColumnOperation(BaseModel):
    type: Literal["derive_column"]
    name: str
    operation: Literal["add", "subtract", "multiply", "divide"]
    left: Operand
    right: Operand


class TopNOperation(BaseModel):
    type: Literal["top_n"]
    column: str
    n: int = Field(default=10, ge=1)
    direction: Literal["asc", "desc"] = "desc"


AnalysisOperation = Annotated[Union[SummarizeOperation, GroupByOperation, FilterOperation, SortOperation,
    CorrelationOperation, ValueCountsOperation, DescriptiveOperation, TimeSeriesOperation,
    DeriveColumnOperation, TopNOperation], Field(discriminator="type")]


class AnalysisPlan(BaseModel):
    operations: list[AnalysisOperation] = Field(min_length=1)


class OperationTrace(BaseModel):
    step: int; type: str; duration_ms: float; input_rows: int; output_rows: int


class AnalysisResult(BaseModel):
    columns: list[str]; rows: list[list[Any]]; row_count: int; truncated: bool; execution_time_ms: float
    operations_executed: list[OperationTrace]; warnings: list[str]; metadata: dict[str, Any]


class AnalysisRunRead(BaseModel):
    id: str; dataset_id: str; status: AnalysisRunStatus; request_json: dict[str, Any]; result_summary_json: dict[str, Any]
    operation_count: int; input_row_count: int | None; output_row_count: int | None; execution_time_ms: float | None
    error_code: str | None; error_message: str | None; created_at: datetime; updated_at: datetime


class AnalysisResponse(BaseModel):
    analysis: AnalysisRunRead
    result: AnalysisResult


class AnalysisListResponse(BaseModel):
    items: list[AnalysisRunRead]; total: int; page: int; page_size: int
