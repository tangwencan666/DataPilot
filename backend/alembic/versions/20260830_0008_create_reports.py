"""create reports"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260830_0008"
down_revision = "20260830_0007"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("dataset_id", sa.String(36), sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_run_id", sa.String(36), sa.ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("status", sa.Enum("PENDING", "GENERATING", "READY", "FAILED", name="report_status", native_enum=False), nullable=False),
        sa.Column("executive_summary", sa.Text(), nullable=False),
        sa.Column("report_json", postgresql.JSONB().with_variant(sa.JSON(), "sqlite"), nullable=False),
        sa.Column("insight_count", sa.Integer(), nullable=False),
        sa.Column("artifact_count", sa.Integer(), nullable=False),
        sa.Column("evidence_truncated", sa.Boolean(), nullable=False),
        sa.Column("generation_time_ms", sa.Float()),
        sa.Column("error_code", sa.String(64)),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_reports_dataset_id", "reports", ["dataset_id"])
    op.create_index("ix_reports_agent_run_id", "reports", ["agent_run_id"])


def downgrade():
    op.drop_index("ix_reports_agent_run_id", table_name="reports")
    op.drop_index("ix_reports_dataset_id", table_name="reports")
    op.drop_table("reports")
