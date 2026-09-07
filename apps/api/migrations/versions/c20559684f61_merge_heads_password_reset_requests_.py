"""merge heads: password_reset_requests + chat_conversation_deleted_at

Revision ID: c20559684f61
Revises: 122f337ae5bf, b5e07c19af23
Create Date: 2026-09-06 21:25:01.886503
"""

from collections.abc import Sequence

revision: str = 'c20559684f61'
down_revision: str | Sequence[str] | None = ('122f337ae5bf', 'b5e07c19af23')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
