"""add password reset requests table

Revision ID: 122f337ae5bf
Revises: a7c31e05b9d4
Create Date: 2026-09-03 09:53:18.659606
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "122f337ae5bf"
down_revision: str | Sequence[str] | None = "a7c31e05b9d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "password_reset_requests",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_password_reset_requests_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_password_reset_requests")),
    )
    op.create_index(
        "ix_password_reset_requests_user_created",
        "password_reset_requests",
        ["user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_password_reset_requests_user_created",
        table_name="password_reset_requests",
    )
    op.drop_table("password_reset_requests")
