"""merge social account and route failure heads

Revision ID: 4bc1feca69fd
Revises: 83e31e2be855, d8f14c7a2b60
Create Date: 2026-08-30 10:32:08.750532
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '4bc1feca69fd'
down_revision: str | Sequence[str] | None = ('83e31e2be855', 'd8f14c7a2b60')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
