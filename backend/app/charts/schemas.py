from datetime import datetime
from typing import Annotated, Any, Literal, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.models import ChartSourceType, ChartStatus

Aggregation = Literal["sum", "mean", "median", "count", "min", "max"]
SortDirection = Literal["asc", "desc"]
Frequency = Literal["day", "week", "month", "quarter", "year"]

class StrictSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200)
    legend: bool = True

    @field_validator("title")
    @classmethod
    def safe_text(cls, value: str) -> str:
        lowered=value.lower()
        if any(token in lowered for token in ("<script", "javascript:", "function(", "function ", "=>", "formatter")):
            raise ValueError("Executable or HTML chart content is forbidden")
        return value

class BarSpec(StrictSpec):
    type: Literal["BAR"]
    category: str
    metric: str
    aggregation: Aggregation = "sum"
    sort: SortDirection = "desc"
    limit: int = Field(20, ge=1, le=100)
    orientation: Literal["vertical", "horizontal"] = "vertical"

class LineSpec(StrictSpec):
    type: Literal["LINE", "AREA"]
    x: str
    y: str
    aggregation: Aggregation = "sum"
    frequency: Frequency | None = None
    series: str | None = None
    sort: SortDirection = "asc"
    limit: int = Field(100, ge=1, le=5000)

class PieSpec(StrictSpec):
    type: Literal["PIE"]
    category: str
    metric: str
    aggregation: Aggregation = "sum"
    sort: SortDirection = "desc"
    limit: int = Field(12, ge=1, le=12)
    include_other: bool = True

class ScatterSpec(StrictSpec):
    type: Literal["SCATTER"]
    x: str
    y: str
    series: str | None = None

class HistogramSpec(StrictSpec):
    type: Literal["HISTOGRAM"]
    column: str
    bins: int = Field(10, ge=5, le=100)

class BoxplotSpec(StrictSpec):
    type: Literal["BOXPLOT"]
    value: str
    category: str | None = None
    limit: int = Field(20, ge=1, le=100)
    show_outliers: bool = True

ChartSpec = Annotated[Union[BarSpec, LineSpec, PieSpec, ScatterSpec, HistogramSpec, BoxplotSpec], Field(discriminator="type")]

class ChartDataSummary(BaseModel):
    source_row_count: int
    rendered_point_count: int
    sampled: bool
    warnings: list[str] = []

class ChartRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str; dataset_id: str; source_type: ChartSourceType; source_reference_id: str | None
    chart_type: str; title: str; spec_json: dict[str, Any]; option_json: dict[str, Any]; status: ChartStatus
    source_row_count: int; rendered_point_count: int; sampled: bool
    error_code: str | None; error_message: str | None; created_at: datetime; updated_at: datetime

class ChartResult(BaseModel):
    chart_id: str
    type: str
    title: str
    spec: dict[str, Any]
    echarts_option: dict[str, Any]
    data_summary: ChartDataSummary
    source_row_count: int
    rendered_point_count: int
    sampled: bool
    warnings: list[str]
    generated_at: datetime

class ChartListResponse(BaseModel):
    items: list[ChartRead]; total: int; page: int; page_size: int
