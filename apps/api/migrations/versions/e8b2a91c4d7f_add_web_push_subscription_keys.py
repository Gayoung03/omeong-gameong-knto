"""add web push subscription keys

Revision ID: e8b2a91c4d7f
Revises: d4f6c8a2e1b3, c7a02c262dc0
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e8b2a91c4d7f"
down_revision: str | Sequence[str] | None = ("d4f6c8a2e1b3", "c7a02c262dc0")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("push_tokens", "token", existing_type=sa.String(255), type_=sa.Text())
    op.add_column("push_tokens", sa.Column("p256dh", sa.Text(), nullable=True))
    op.add_column("push_tokens", sa.Column("auth", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("push_tokens", "auth")
    op.drop_column("push_tokens", "p256dh")
    op.alter_column("push_tokens", "token", existing_type=sa.Text(), type_=sa.String(255))
