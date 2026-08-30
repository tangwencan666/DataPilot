import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, Enum, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DatasetStatus(str, enum.Enum):
    UPLOADING = "UPLOADING"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"


class ProfileStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    READY = "READY"
    FAILED = "FAILED"


class QueryStatus(str, enum.Enum):
    PENDING = "PENDING"
    GENERATING = "GENERATING"
    VALIDATING = "VALIDATING"
    EXECUTING = "EXECUTING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class AnalysisRunStatus(str, enum.Enum):
    PENDING = "PENDING"
    VALIDATING = "VALIDATING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"


class ChartStatus(str, enum.Enum):
    PENDING = "PENDING"
    GENERATING = "GENERATING"
    READY = "READY"
    FAILED = "FAILED"


class ChartSourceType(str, enum.Enum):
    DATASET = "DATASET"
    QUERY = "QUERY"
    ANALYSIS = "ANALYSIS"

class AgentRunStatus(str, enum.Enum):
    PENDING="PENDING"; PLANNING="PLANNING"; VALIDATING="VALIDATING"; RUNNING="RUNNING"; SUCCEEDED="SUCCEEDED"; FAILED="FAILED"; PARTIAL="PARTIAL"

class AgentStepStatus(str, enum.Enum):
    PENDING="PENDING"; RUNNING="RUNNING"; SUCCEEDED="SUCCEEDED"; FAILED="FAILED"; SKIPPED="SKIPPED"


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    column_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[DatasetStatus] = mapped_column(
        Enum(DatasetStatus, name="dataset_status", native_enum=False), nullable=False, default=DatasetStatus.UPLOADING
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class DatasetProfile(Base):
    __tablename__ = "dataset_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id: Mapped[str] = mapped_column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, unique=True)
    status: Mapped[ProfileStatus] = mapped_column(Enum(ProfileStatus, name="profile_status", native_enum=False), nullable=False, default=ProfileStatus.PENDING)
    profile_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    column_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_row_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    missing_cell_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    missing_cell_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    profile_json: Mapped[dict[str, Any]] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class AnalysisQuery(Base):
    __tablename__ = "analysis_queries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id: Mapped[str] = mapped_column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    generated_sql: Mapped[str | None] = mapped_column(Text, nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[QueryStatus] = mapped_column(Enum(QueryStatus, name="query_status", native_enum=False), nullable=False, default=QueryStatus.PENDING)
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    execution_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id: Mapped[str] = mapped_column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[AnalysisRunStatus] = mapped_column(Enum(AnalysisRunStatus, name="analysis_run_status", native_enum=False), nullable=False, default=AnalysisRunStatus.PENDING)
    request_json: Mapped[dict[str, Any]] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    result_summary_json: Mapped[dict[str, Any]] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict)
    operation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    input_row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    execution_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Chart(Base):
    __tablename__ = "charts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id: Mapped[str] = mapped_column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    source_type: Mapped[ChartSourceType] = mapped_column(Enum(ChartSourceType, name="chart_source_type", native_enum=False), nullable=False)
    source_reference_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    chart_type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    spec_json: Mapped[dict[str, Any]] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    option_json: Mapped[dict[str, Any]] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict)
    status: Mapped[ChartStatus] = mapped_column(Enum(ChartStatus, name="chart_status", native_enum=False), nullable=False, default=ChartStatus.PENDING)
    source_row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rendered_point_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sampled: Mapped[bool] = mapped_column(nullable=False, default=False)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class AgentRun(Base):
    __tablename__="agent_runs"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid.uuid4()))
    dataset_id: Mapped[str]=mapped_column(String(36),ForeignKey("datasets.id",ondelete="CASCADE"),nullable=False,index=True)
    user_question: Mapped[str]=mapped_column(Text,nullable=False); goal: Mapped[str|None]=mapped_column(Text,nullable=True)
    status: Mapped[AgentRunStatus]=mapped_column(Enum(AgentRunStatus,name="agent_run_status",native_enum=False),nullable=False,default=AgentRunStatus.PENDING)
    planner_summary: Mapped[str|None]=mapped_column(Text,nullable=True); step_count: Mapped[int]=mapped_column(Integer,nullable=False,default=0); completed_step_count: Mapped[int]=mapped_column(Integer,nullable=False,default=0)
    final_summary_json: Mapped[dict[str,Any]]=mapped_column(JSON().with_variant(JSONB,"postgresql"),nullable=False,default=dict)
    error_code: Mapped[str|None]=mapped_column(String(64),nullable=True); error_message: Mapped[str|None]=mapped_column(Text,nullable=True)
    context_metadata_json: Mapped[dict[str,Any]]=mapped_column(JSON().with_variant(JSONB,"postgresql"),nullable=False,default=dict)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),nullable=False); updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),onupdate=func.now(),nullable=False)

class AgentStepRun(Base):
    __tablename__="agent_step_runs"
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid.uuid4()))
    agent_run_id: Mapped[str]=mapped_column(String(36),ForeignKey("agent_runs.id",ondelete="CASCADE"),nullable=False,index=True)
    step_id: Mapped[str]=mapped_column(String(64),nullable=False); sequence: Mapped[int]=mapped_column(Integer,nullable=False); tool_name: Mapped[str]=mapped_column(String(16),nullable=False); purpose: Mapped[str]=mapped_column(Text,nullable=False)
    status: Mapped[AgentStepStatus]=mapped_column(Enum(AgentStepStatus,name="agent_step_status",native_enum=False),nullable=False,default=AgentStepStatus.PENDING)
    input_summary_json: Mapped[dict[str,Any]]=mapped_column(JSON().with_variant(JSONB,"postgresql"),nullable=False,default=dict); output_summary_json: Mapped[dict[str,Any]]=mapped_column(JSON().with_variant(JSONB,"postgresql"),nullable=False,default=dict)
    artifact_type: Mapped[str|None]=mapped_column(String(32),nullable=True); artifact_id: Mapped[str|None]=mapped_column(String(36),nullable=True); execution_time_ms: Mapped[float|None]=mapped_column(Float,nullable=True)
    error_code: Mapped[str|None]=mapped_column(String(64),nullable=True); error_message: Mapped[str|None]=mapped_column(Text,nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),nullable=False); updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),onupdate=func.now(),nullable=False)
