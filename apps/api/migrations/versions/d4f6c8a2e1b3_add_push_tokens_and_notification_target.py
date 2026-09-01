"""add push tokens and notification target

Revision ID: d4f6c8a2e1b3
Revises: 0a20d1f6a743
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d4f6c8a2e1b3"
down_revision: str | Sequence[str] | None = "0a20d1f6a743"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("notifications", sa.Column("target_id", postgresql.UUID(), nullable=True))
    op.create_table(
        "push_tokens",
        sa.Column("id", postgresql.UUID(), nullable=False),
        sa.Column("user_id", postgresql.UUID(), nullable=False),
        sa.Column("token", sa.String(length=255), nullable=False),
        sa.Column("platform", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index("ix_push_tokens_user", "push_tokens", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_push_tokens_user", table_name="push_tokens")
    op.drop_table("push_tokens")
    op.drop_column("notifications", "target_id")
