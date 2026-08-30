"""create dataset profiles table

Revision ID: 20260830_0002
Revises: 20260830_0001
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260830_0002"
down_revision: Union[str, Sequence[str], None] = "20260830_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    profile_json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
    op.create_table(
        "dataset_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("dataset_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.Enum("PENDING", "RUNNING", "READY", "FAILED", name="profile_status", native_enum=False), nullable=False),
        sa.Column("profile_version", sa.Integer(), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("column_count", sa.Integer(), nullable=False),
        sa.Column("duplicate_row_count", sa.Integer(), nullable=False),
        sa.Column("duplicate_row_ratio", sa.Float(), nullable=False),
        sa.Column("missing_cell_count", sa.BigInteger(), nullable=False),
        sa.Column("missing_cell_ratio", sa.Float(), nullable=False),
        sa.Column("quality_score", sa.Float(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("profile_json", profile_json_type, nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dataset_id"),
    )


def downgrade() -> None:
    op.drop_table("dataset_profiles")
