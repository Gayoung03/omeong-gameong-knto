"""add places.cuisine

Revision ID: c1a2b3d4e5f6
Revises: 3d6f8a1b2c4e
Create Date: 2026-09-08 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c1a2b3d4e5f6"
down_revision: str | Sequence[str] | None = "a1b7c3d5e2f4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# 음식점·카페 세부 음식 종류(한식·중식·일식 …). enum 아님(자유 varchar).
# 가산적 nullable ADD COLUMN — 카카오 로컬 category_name 파싱 배치가 채운다.
def upgrade() -> None:
    op.add_column("places", sa.Column("cuisine", sa.String(length=30), nullable=True))


def downgrade() -> None:
    op.drop_column("places", "cuisine")
