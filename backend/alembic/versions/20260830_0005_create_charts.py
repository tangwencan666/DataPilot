"""create charts

Revision ID: 20260830_0005
Revises: 20260830_0004
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260830_0005"
down_revision: Union[str, None] = "20260830_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "charts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("dataset_id", sa.String(36), sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_type", sa.Enum("DATASET", "QUERY", "ANALYSIS", name="chart_source_type", native_enum=False), nullable=False),
        sa.Column("source_reference_id", sa.String(36), nullable=True),
        sa.Column("chart_type", sa.String(32), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("spec_json", postgresql.JSONB().with_variant(sa.JSON(), "sqlite"), nullable=False),
        sa.Column("option_json", postgresql.JSONB().with_variant(sa.JSON(), "sqlite"), nullable=False),
        sa.Column("status", sa.Enum("PENDING", "GENERATING", "READY", "FAILED", name="chart_status", native_enum=False), nullable=False),
        sa.Column("source_row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rendered_point_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sampled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_charts_dataset_id", "charts", ["dataset_id"])


def downgrade() -> None:
    op.drop_index("ix_charts_dataset_id", table_name="charts")
    op.drop_table("charts")
