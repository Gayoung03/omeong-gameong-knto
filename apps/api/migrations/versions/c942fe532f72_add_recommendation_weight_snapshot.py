"""add recommendation weight snapshot

Revision ID: c942fe532f72
Revises: 0072d3eaa143
Create Date: 2026-08-27 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c942fe532f72"
down_revision: str | Sequence[str] | None = "0072d3eaa143"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("route_requests", sa.Column("priority_preset", sa.String(30), nullable=True))
    op.add_column(
        "route_requests",
        sa.Column("applied_weights", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("route_requests", "applied_weights")
    op.drop_column("route_requests", "priority_preset")
