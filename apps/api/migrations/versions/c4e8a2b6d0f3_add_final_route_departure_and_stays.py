"""add final route departure and stays

Revision ID: c4e8a2b6d0f3
Revises: a1f5c9d3e7b2
Create Date: 2026-09-13 12:00:00.000000
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "c4e8a2b6d0f3"
down_revision: str | Sequence[str] | None = "a1f5c9d3e7b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


routes = sa.table(
    "routes",
    sa.column("id", UUID(as_uuid=True)),
    sa.column("route_request_id", UUID(as_uuid=True)),
)
route_request_stays = sa.table(
    "route_request_stays",
    sa.column("route_request_id", UUID(as_uuid=True)),
    sa.column("place_id", UUID(as_uuid=True)),
    sa.column("name", sa.String()),
    sa.column("address", sa.Text()),
    sa.column("latitude", sa.Numeric(10, 7)),
    sa.column("longitude", sa.Numeric(10, 7)),
    sa.column("check_in_at", sa.DateTime(timezone=True)),
    sa.column("check_out_at", sa.DateTime(timezone=True)),
)
route_stays = sa.table(
    "route_stays",
    sa.column("id", UUID(as_uuid=True)),
    sa.column("route_id", UUID(as_uuid=True)),
    sa.column("place_id", UUID(as_uuid=True)),
    sa.column("name", sa.String()),
    sa.column("address", sa.Text()),
    sa.column("latitude", sa.Numeric(10, 7)),
    sa.column("longitude", sa.Numeric(10, 7)),
    sa.column("check_in_at", sa.DateTime(timezone=True)),
    sa.column("check_out_at", sa.DateTime(timezone=True)),
)


def upgrade() -> None:
    op.add_column("routes", sa.Column("departure_location", sa.String(length=100)))
    op.add_column("routes", sa.Column("departure_place_id", UUID(as_uuid=True)))
    op.create_foreign_key(
        op.f("fk_routes_departure_place_id_places"),
        "routes",
        "places",
        ["departure_place_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_table(
        "route_stays",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("route_id", UUID(as_uuid=True), nullable=False),
        sa.Column("place_id", UUID(as_uuid=True)),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("address", sa.Text()),
        sa.Column("latitude", sa.Numeric(10, 7)),
        sa.Column("longitude", sa.Numeric(10, 7)),
        sa.Column("check_in_at", sa.DateTime(timezone=True)),
        sa.Column("check_out_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "check_out_at IS NULL OR check_in_at IS NULL OR check_out_at > check_in_at",
            name=op.f("ck_route_stays_date_order"),
        ),
        sa.ForeignKeyConstraint(
            ["place_id"],
            ["places.id"],
            name=op.f("fk_route_stays_place_id_places"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["route_id"],
            ["routes.id"],
            name=op.f("fk_route_stays_route_id_routes"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_route_stays")),
    )
    op.create_index("ix_route_stays_route", "route_stays", ["route_id"])

    # 기존 추천 여행의 요청 스냅샷을 최종 여행 저장소로 옮긴다.
    op.execute(
        """
        UPDATE routes AS r
        SET departure_location = COALESCE(rr.departure_location, p.name),
            departure_place_id = rr.departure_place_id
        FROM route_requests AS rr
        LEFT JOIN places AS p ON p.id = rr.departure_place_id
        WHERE r.route_request_id = rr.id
        """
    )
    bind = op.get_bind()
    rows = bind.execute(
        sa.select(
            routes.c.id.label("route_id"),
            route_request_stays.c.place_id,
            route_request_stays.c.name,
            route_request_stays.c.address,
            route_request_stays.c.latitude,
            route_request_stays.c.longitude,
            route_request_stays.c.check_in_at,
            route_request_stays.c.check_out_at,
        ).join(
            route_request_stays,
            route_request_stays.c.route_request_id == routes.c.route_request_id,
        )
    ).mappings()
    values = [{"id": uuid.uuid4(), **dict(row)} for row in rows]
    if values:
        bind.execute(sa.insert(route_stays), values)


def downgrade() -> None:
    op.drop_index("ix_route_stays_route", table_name="route_stays")
    op.drop_table("route_stays")
    op.drop_constraint(
        op.f("fk_routes_departure_place_id_places"),
        "routes",
        type_="foreignkey",
    )
    op.drop_column("routes", "departure_place_id")
    op.drop_column("routes", "departure_location")
