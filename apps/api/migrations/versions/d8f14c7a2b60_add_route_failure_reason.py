"""add route failure reason

Revision ID: d8f14c7a2b60
Revises: 31a78f4d2c9b
Create Date: 2026-08-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d8f14c7a2b60"
down_revision: str | Sequence[str] | None = "31a78f4d2c9b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

failure_reason = sa.Enum(
    "LOCATION_NOT_FOUND",
    "NO_RECOMMENDABLE_PLACES",
    "DINNER_RESTAURANT_SHORTAGE",
    "ROUTE_PROVIDER_FAILED",
    "GENERATION_TIMEOUT",
    "UNKNOWN",
    name="route_failure_reason",
)


def upgrade() -> None:
    failure_reason.create(op.get_bind(), checkfirst=True)
    op.add_column("routes", sa.Column("failure_reason", failure_reason))


def downgrade() -> None:
    op.drop_column("routes", "failure_reason")
    failure_reason.drop(op.get_bind(), checkfirst=True)
