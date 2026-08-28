"""add route location snapshots

Revision ID: 31a78f4d2c9b
Revises: 972f1e5041f8
Create Date: 2026-08-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "31a78f4d2c9b"
down_revision: str | Sequence[str] | None = "972f1e5041f8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("route_requests", sa.Column("departure_latitude", sa.Numeric(10, 7)))
    op.add_column("route_requests", sa.Column("departure_longitude", sa.Numeric(10, 7)))
    op.add_column("route_request_stays", sa.Column("latitude", sa.Numeric(10, 7)))
    op.add_column("route_request_stays", sa.Column("longitude", sa.Numeric(10, 7)))
    op.add_column("route_items", sa.Column("custom_address", sa.Text()))
    op.add_column("route_items", sa.Column("latitude", sa.Numeric(10, 7)))
    op.add_column("route_items", sa.Column("longitude", sa.Numeric(10, 7)))


def downgrade() -> None:
    op.drop_column("route_items", "longitude")
    op.drop_column("route_items", "latitude")
    op.drop_column("route_items", "custom_address")
    op.drop_column("route_request_stays", "longitude")
    op.drop_column("route_request_stays", "latitude")
    op.drop_column("route_requests", "departure_longitude")
    op.drop_column("route_requests", "departure_latitude")
