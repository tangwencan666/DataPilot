from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field
from app.models import ReportStatus


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Importance(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class StepEvidence(Strict):
    step_id: str
    tool: str
    purpose: str
    status: str
    was_repaired: bool
    attempt_count: int
    result_summary: str = ""
    row_count: int = 0
    warnings: list[str] = []
    artifact_type: str | None = None
    artifact_id: str | None = None


class ArtifactEvidence(Strict):
    ref: str
    type: str
    id: str
    title: str
    summary: str


class ReportEvidence(Strict):
    dataset_summary: dict[str, Any]
    question: str
    goal: str | None
    planner_summary: str | None
    execution_summary: dict[str, int]
    step_evidence: list[StepEvidence]
    profile_evidence: dict[str, Any]
    artifact_evidence: list[ArtifactEvidence]
    final_synthesis: dict[str, Any]
    limitations: list[str]
    evidence_refs: list[str]
    evidence_truncated: bool = False


class Insight(Strict):
    id: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
    title: str = Field(min_length=1, max_length=200)
    statement: str = Field(min_length=1, max_length=2000)
    importance: Importance
    confidence: float = Field(ge=0, le=1)
    evidence_refs: list[str] = Field(min_length=1, max_length=20)
    limitations: list[str] = Field(default_factory=list, max_length=10)


class InsightSet(Strict):
    insights: list[Insight]


class ReportDraft(Strict):
    title: str = Field(min_length=1, max_length=200)
    executive_summary: str = Field(min_length=1, max_length=5000)
    detailed_analysis: str = Field(min_length=1, max_length=10000)
    conclusion: str = Field(min_length=1, max_length=3000)
    limitations: list[str] = Field(default_factory=list, max_length=20)


class ReportArtifact(Strict):
    type: str
    id: str
    title: str
    summary: str


class ReportSection(Strict):
    key: str
    title: str
    content: str


class ReportDocument(Strict):
    title: str
    executive_summary: str
    sections: list[ReportSection]
    key_insights: list[Insight]
    limitations: list[str]
    methodology: list[str]
    artifacts: list[ReportArtifact]
    source_status: str
    generated_at: datetime


class ReportCreate(Strict):
    agent_run_id: str


class ReportRead(Strict):
    id: str
    dataset_id: str
    agent_run_id: str
    title: str
    status: ReportStatus
    executive_summary: str
    report: ReportDocument | None
    insight_count: int
    artifact_count: int
    evidence_truncated: bool
    generation_time_ms: float | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class ReportList(Strict):
    items: list[ReportRead]
    total: int
    page: int
    page_size: int
