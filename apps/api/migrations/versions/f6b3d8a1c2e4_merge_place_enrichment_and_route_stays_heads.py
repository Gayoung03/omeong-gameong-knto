"""merge place enrichment and route stays migration heads

Revision ID: f6b3d8a1c2e4
Revises: e4a1c7d9b203, c4e8a2b6d0f3
Create Date: 2026-09-13 15:00:00
"""

from collections.abc import Sequence

revision: str = "f6b3d8a1c2e4"
down_revision: tuple[str, str] = ("e4a1c7d9b203", "c4e8a2b6d0f3")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
