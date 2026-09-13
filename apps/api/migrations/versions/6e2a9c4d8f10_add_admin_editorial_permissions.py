"""add admin editorial permissions and audit logs

Revision ID: 6e2a9c4d8f10
Revises: 3d6f8a1b2c4e
Create Date: 2026-09-07 16:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "6e2a9c4d8f10"
down_revision: str | Sequence[str] | None = "3d6f8a1b2c4e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_admin", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.create_table(
        "admin_editorial_audit_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("story_id", sa.UUID(), nullable=False),
        sa.Column("actor_user_id", sa.UUID(), nullable=False),
        sa.Column("action", sa.String(length=30), nullable=False),
        sa.Column("previous_status", sa.String(length=20), nullable=True),
        sa.Column("next_status", sa.String(length=20), nullable=True),
        sa.Column(
            "changes",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["users.id"], name=op.f("fk_admin_audit_actor_users")
        ),
        sa.ForeignKeyConstraint(
            ["story_id"],
            ["editorial_stories.id"],
            name=op.f("fk_admin_audit_story_editorial_stories"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_admin_editorial_audit_logs")),
    )
    op.create_index(
        "ix_admin_editorial_audit_story_created",
        "admin_editorial_audit_logs",
        ["story_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_admin_editorial_audit_story_created",
        table_name="admin_editorial_audit_logs",
    )
    op.drop_table("admin_editorial_audit_logs")
    op.drop_column("users", "is_admin")
