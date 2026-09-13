"""add route_items.slot_status and route_item_candidates

Revision ID: d2b3c4e5f6a7
Revises: c1a2b3d4e5f6
Create Date: 2026-09-08 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d2b3c4e5f6a7"
down_revision: str | Sequence[str] | None = "c1a2b3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# 슬롯 상태(route-redesign §3.1). 기존 행은 전부 filled(DEFAULT)라 백필 불필요.
# CHECK 는 팀 DB 에 place_id·custom_place_name 둘 다 NULL 인 행이 0건임을 확인해 바로
# VALID 로 건다(있었다면 NOT VALID → 정리 → VALIDATE 선례 ck_users_local_requires_password).
route_item_slot_status = postgresql.ENUM(
    "filled",
    "unfilled",
    "needs_verification",
    name="route_item_slot_status",
    create_type=False,
)


def upgrade() -> None:
    route_item_slot_status.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "route_items",
        sa.Column(
            "slot_status",
            route_item_slot_status,
            server_default="filled",
            nullable=False,
        ),
    )
    op.create_check_constraint(
        op.f("ck_route_items_slot_status_place_consistency"),
        "route_items",
        "(slot_status = 'unfilled' AND place_id IS NULL AND custom_place_name IS NULL) "
        "OR (slot_status <> 'unfilled' "
        "AND (place_id IS NOT NULL OR custom_place_name IS NOT NULL))",
    )

    op.create_table(
        "route_item_candidates",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("route_item_id", sa.UUID(), nullable=False),
        sa.Column("place_id", sa.UUID(), nullable=False),
        sa.Column("rank", sa.SmallInteger(), nullable=False),
        sa.Column("recommendation_score", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("recommendation_reason", sa.Text(), nullable=True),
        sa.Column(
            "requires_verification",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "rank BETWEEN 1 AND 3", name=op.f("ck_route_item_candidates_rank_range")
        ),
        sa.ForeignKeyConstraint(
            ["route_item_id"],
            ["route_items.id"],
            name=op.f("fk_route_item_candidates_route_item_id_route_items"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["place_id"],
            ["places.id"],
            name=op.f("fk_route_item_candidates_place_id_places"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_route_item_candidates")),
        sa.UniqueConstraint(
            "route_item_id", "rank", name=op.f("uq_route_item_candidates_route_item_id_rank")
        ),
    )
    op.create_index(
        "ix_route_item_candidates_place_id", "route_item_candidates", ["place_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_route_item_candidates_place_id", table_name="route_item_candidates")
    op.drop_table("route_item_candidates")
    op.drop_constraint(
        op.f("ck_route_items_slot_status_place_consistency"), "route_items", type_="check"
    )
    op.drop_column("route_items", "slot_status")
    route_item_slot_status.drop(op.get_bind(), checkfirst=True)
