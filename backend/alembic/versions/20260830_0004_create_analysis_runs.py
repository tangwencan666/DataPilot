"""create analysis runs table

Revision ID: 20260830_0004
Revises: 20260830_0003
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260830_0004"
down_revision: Union[str, Sequence[str], None] = "20260830_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
    op.create_table("analysis_runs",
        sa.Column("id", sa.String(36), nullable=False), sa.Column("dataset_id", sa.String(36), nullable=False),
        sa.Column("status", sa.Enum("PENDING", "VALIDATING", "RUNNING", "SUCCEEDED", "FAILED", "TIMED_OUT", name="analysis_run_status", native_enum=False), nullable=False),
        sa.Column("request_json", json_type, nullable=False), sa.Column("result_summary_json", json_type, nullable=False),
        sa.Column("operation_count", sa.Integer(), nullable=False), sa.Column("input_row_count", sa.Integer(), nullable=True),
        sa.Column("output_row_count", sa.Integer(), nullable=True), sa.Column("execution_time_ms", sa.Float(), nullable=True),
        sa.Column("error_code", sa.String(64), nullable=True), sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_analysis_runs_dataset_id", "analysis_runs", ["dataset_id"])


def downgrade() -> None:
    op.drop_index("ix_analysis_runs_dataset_id", table_name="analysis_runs")
    op.drop_table("analysis_runs")
