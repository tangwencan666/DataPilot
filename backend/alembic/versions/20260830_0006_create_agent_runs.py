"""create agent runs and steps

Revision ID: 20260830_0006
Revises: 20260830_0005
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260830_0006"
down_revision = "20260830_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
json_type = postgresql.JSONB().with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("dataset_id", sa.String(36), sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_question", sa.Text(), nullable=False),
        sa.Column("goal", sa.Text()),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING", "PLANNING", "VALIDATING", "RUNNING", "SUCCEEDED", "FAILED", "PARTIAL", name="agent_run_status", native_enum=False
            ),
            nullable=False,
        ),
        sa.Column("planner_summary", sa.Text()),
        sa.Column("step_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_step_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("final_summary_json", json_type, nullable=False),
        sa.Column("error_code", sa.String(64)),
        sa.Column("error_message", sa.Text()),
        sa.Column("context_metadata_json", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_agent_runs_dataset_id", "agent_runs", ["dataset_id"])
    op.create_table(
        "agent_step_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("agent_run_id", sa.String(36), sa.ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_id", sa.String(64), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("tool_name", sa.String(16), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PENDING", "RUNNING", "SUCCEEDED", "FAILED", "SKIPPED", name="agent_step_status", native_enum=False),
            nullable=False,
        ),
        sa.Column("input_summary_json", json_type, nullable=False),
        sa.Column("output_summary_json", json_type, nullable=False),
        sa.Column("artifact_type", sa.String(32)),
        sa.Column("artifact_id", sa.String(36)),
        sa.Column("execution_time_ms", sa.Float()),
        sa.Column("error_code", sa.String(64)),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_agent_step_runs_agent_run_id", "agent_step_runs", ["agent_run_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_step_runs_agent_run_id", table_name="agent_step_runs")
    op.drop_table("agent_step_runs")
    op.drop_index("ix_agent_runs_dataset_id", table_name="agent_runs")
    op.drop_table("agent_runs")
