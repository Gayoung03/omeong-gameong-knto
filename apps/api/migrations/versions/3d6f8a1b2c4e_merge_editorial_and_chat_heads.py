"""merge editorial stories and chat migration heads

Revision ID: 3d6f8a1b2c4e
Revises: c20559684f61, d8f4a21c9b70
Create Date: 2026-09-07 13:00:00
"""

from collections.abc import Sequence

revision: str = "3d6f8a1b2c4e"
down_revision: tuple[str, str] = ("c20559684f61", "d8f4a21c9b70")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
