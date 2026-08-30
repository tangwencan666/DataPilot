from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SemanticType(str, Enum):
    NUMERIC = "NUMERIC"
    CATEGORICAL = "CATEGORICAL"
    BOOLEAN = "BOOLEAN"
    DATETIME = "DATETIME"
    TEXT = "TEXT"
    UNKNOWN = "UNKNOWN"


class IssueSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class TopValue(BaseModel):
    value: Any
    count: int
    ratio: float


class NumericProfile(BaseModel):
    min: float | None = None
    max: float | None = None
    mean: float | None = None
    median: float | None = None
    std: float | None = None
    variance: float | None = None
    q1: float | None = None
    q3: float | None = None
    iqr: float | None = None
    p01: float | None = None
    p05: float | None = None
    p95: float | None = None
    p99: float | None = None
    zero_count: int
    zero_ratio: float
    negative_count: int
    negative_ratio: float
    outlier_count: int
    outlier_ratio: float
    infinite_count: int


class CategoricalProfile(BaseModel):
    unique_count: int
    top_values: list[TopValue]
    is_high_cardinality: bool


class TextProfile(BaseModel):
    average_length: float | None = None
    min_length: int | None = None
    max_length: int | None = None
    empty_string_count: int
    top_values: list[TopValue]


class DatetimeProfile(BaseModel):
    min_datetime: datetime | None = None
    max_datetime: datetime | None = None
    range_days: float | None = None
    year_distribution: dict[str, int]
    month_distribution: dict[str, int]
    weekday_distribution: dict[str, int]


class BooleanProfile(BaseModel):
    true_count: int
    false_count: int
    true_ratio: float
    false_ratio: float


class ColumnProfile(BaseModel):
    name: str
    physical_dtype: str
    semantic_type: SemanticType
    count: int
    non_null_count: int
    missing_count: int
    missing_ratio: float
    unique_count: int
    unique_ratio: float
    is_constant: bool
    is_all_missing: bool
    sample_values: list[Any]
    numeric: NumericProfile | None = None
    categorical: CategoricalProfile | None = None
    text: TextProfile | None = None
    datetime: DatetimeProfile | None = None
    boolean: BooleanProfile | None = None


class CorrelationPair(BaseModel):
    column_a: str
    column_b: str
    correlation: float


class DataQualityIssue(BaseModel):
    code: str
    severity: IssueSeverity
    title: str
    description: str
    column: str | None = None
    metric: str
    value: float | int | str


class DatasetProfileSummary(BaseModel):
    row_count: int
    column_count: int
    total_cells: int
    missing_cell_count: int
    missing_cell_ratio: float
    duplicate_row_count: int
    duplicate_row_ratio: float
    numeric_column_count: int
    categorical_column_count: int
    text_column_count: int
    datetime_column_count: int
    boolean_column_count: int
    constant_column_count: int
    all_missing_column_count: int
    high_cardinality_column_count: int
    quality_score: float = Field(ge=0, le=100)


class SamplingInfo(BaseModel):
    is_sampled: bool
    sampled_row_count: int
    source_row_count: int
    statistics_scope: str


class ProfileResult(BaseModel):
    summary: DatasetProfileSummary
    sampling: SamplingInfo
    columns: list[ColumnProfile]
    correlations: list[CorrelationPair]
    issues: list[DataQualityIssue]
