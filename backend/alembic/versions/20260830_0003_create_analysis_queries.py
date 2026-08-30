"""create analysis queries table

Revision ID: 20260830_0003
Revises: 20260830_0002
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "20260830_0003"
down_revision: Union[str, Sequence[str], None] = "20260830_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "analysis_queries",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("dataset_id", sa.String(36), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("generated_sql", sa.Text(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("status", sa.Enum("PENDING", "GENERATING", "VALIDATING", "EXECUTING", "SUCCEEDED", "FAILED", name="query_status", native_enum=False), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("execution_time_ms", sa.Float(), nullable=True),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_analysis_queries_dataset_id", "analysis_queries", ["dataset_id"])


def downgrade() -> None:
    op.drop_index("ix_analysis_queries_dataset_id", table_name="analysis_queries")
    op.drop_table("analysis_queries")
