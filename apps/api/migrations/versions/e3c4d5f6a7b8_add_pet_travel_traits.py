"""add pets travel traits and route_request_pets.energy_level

Revision ID: e3c4d5f6a7b8
Revises: d2b3c4e5f6a7
Create Date: 2026-09-08 13:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e3c4d5f6a7b8"
down_revision: str | Sequence[str] | None = "d2b3c4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# 반려동물 여행 특성(route-redesign §3.3·§3.4). 전부 nullable·기본값 없음(NULL=규칙 미적용).
# 값 집합이 같아도 activity/sociability/energy 는 별도 타입(한쪽 값 확장이 번지지 않게).
pet_activity_level = postgresql.ENUM(
    "low", "normal", "high", name="pet_activity_level", create_type=False
)
pet_sociability_level = postgresql.ENUM(
    "low", "normal", "high", name="pet_sociability_level", create_type=False
)
pet_energy_level = postgresql.ENUM(
    "low", "normal", "high", name="pet_energy_level", create_type=False
)


def upgrade() -> None:
    pet_activity_level.create(op.get_bind(), checkfirst=True)
    pet_sociability_level.create(op.get_bind(), checkfirst=True)
    pet_energy_level.create(op.get_bind(), checkfirst=True)

    op.add_column("pets", sa.Column("activity_level", pet_activity_level, nullable=True))
    op.add_column("pets", sa.Column("sociability", pet_sociability_level, nullable=True))
    op.add_column("pets", sa.Column("car_sickness", sa.Boolean(), nullable=True))
    op.add_column(
        "route_request_pets", sa.Column("energy_level", pet_energy_level, nullable=True)
    )


def downgrade() -> None:
    op.drop_column("route_request_pets", "energy_level")
    op.drop_column("pets", "car_sickness")
    op.drop_column("pets", "sociability")
    op.drop_column("pets", "activity_level")
    pet_energy_level.drop(op.get_bind(), checkfirst=True)
    pet_sociability_level.drop(op.get_bind(), checkfirst=True)
    pet_activity_level.drop(op.get_bind(), checkfirst=True)
