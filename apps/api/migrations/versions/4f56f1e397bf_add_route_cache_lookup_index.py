"""add route cache lookup index

Revision ID: 4f56f1e397bf
Revises: 91540737bf42
Create Date: 2026-08-31 16:45:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "4f56f1e397bf"
down_revision: str | Sequence[str] | None = "91540737bf42"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# route_calculation_cache 조회용 복합 인덱스(ai-io-column-design 8.1-5).
# 좌표 4개 + transport 로 찾는 조회가 현재 expires_at 단일 인덱스뿐이라 Seq Scan 이다.
# expires_at 은 INCLUDE 로 얹어 인덱스만으로 유효성 판정(index-only scan).
def upgrade() -> None:
    op.create_index(
        "ix_route_calculation_cache_lookup",
        "route_calculation_cache",
        [
            "origin_latitude",
            "origin_longitude",
            "destination_latitude",
            "destination_longitude",
            "transport",
        ],
        postgresql_include=["expires_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_route_calculation_cache_lookup", table_name="route_calculation_cache"
    )
