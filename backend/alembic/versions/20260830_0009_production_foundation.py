"""add users, dataset ownership, and production indexes"""

from alembic import op
import sqlalchemy as sa

revision = "20260830_0009"
down_revision = "20260830_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    # Nullable preserves pre-authentication datasets. New authenticated uploads always set an owner.
    with op.batch_alter_table("datasets") as batch:
        batch.add_column(sa.Column("owner_user_id", sa.String(36), nullable=True))
        batch.create_foreign_key("fk_datasets_owner_user_id_users", "users", ["owner_user_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_datasets_owner_user_id", "datasets", ["owner_user_id"])
    op.create_index("ix_datasets_created_at", "datasets", ["created_at"])
    op.create_index("ix_agent_runs_created_at", "agent_runs", ["created_at"])
    op.create_index("ix_reports_created_at", "reports", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_reports_created_at", table_name="reports")
    op.drop_index("ix_agent_runs_created_at", table_name="agent_runs")
    op.drop_index("ix_datasets_created_at", table_name="datasets")
    op.drop_index("ix_datasets_owner_user_id", table_name="datasets")
    with op.batch_alter_table("datasets") as batch:
        batch.drop_constraint("fk_datasets_owner_user_id_users", type_="foreignkey")
        batch.drop_column("owner_user_id")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
