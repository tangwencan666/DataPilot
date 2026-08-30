"""create agent step attempts

Revision ID: 20260830_0007
Revises: 20260830_0006
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260830_0007"
down_revision = "20260830_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
json_type = postgresql.JSONB().with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    op.add_column("agent_step_runs", sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("agent_step_runs", sa.Column("repair_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("agent_step_runs", sa.Column("final_attempt_id", sa.String(36), nullable=True))
    op.create_table(
        "agent_step_attempts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("agent_step_run_id", sa.String(36), sa.ForeignKey("agent_step_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("attempt_type", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("input_summary_json", json_type, nullable=False),
        sa.Column("observation_json", json_type, nullable=False),
        sa.Column("repair_summary_json", json_type, nullable=False),
        sa.Column("execution_time_ms", sa.Float()),
        sa.Column("error_code", sa.String(64)),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_agent_step_attempts_agent_step_run_id", "agent_step_attempts", ["agent_step_run_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_step_attempts_agent_step_run_id", table_name="agent_step_attempts")
    op.drop_table("agent_step_attempts")
    op.drop_column("agent_step_runs", "final_attempt_id")
    op.drop_column("agent_step_runs", "repair_count")
    op.drop_column("agent_step_runs", "attempt_count")
