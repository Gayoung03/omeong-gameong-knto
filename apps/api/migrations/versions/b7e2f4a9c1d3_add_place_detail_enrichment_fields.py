"""add place detail enrichment fields

Revision ID: b7e2f4a9c1d3
Revises: a1f5c9d3e7b2
Create Date: 2026-09-11 17:20:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b7e2f4a9c1d3"
down_revision: str | Sequence[str] | None = "a1f5c9d3e7b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE data_provider ADD VALUE IF NOT EXISTS 'mfds'")
    op.add_column("places", sa.Column("closed_days_raw", sa.Text(), nullable=True))
    op.add_column("places", sa.Column("image_urls", sa.ARRAY(sa.Text()), nullable=True))
    op.add_column(
        "place_pet_policies",
        sa.Column("required_items", sa.ARRAY(sa.String()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("place_pet_policies", "required_items")
    op.drop_column("places", "image_urls")
    op.drop_column("places", "closed_days_raw")
    # PostgreSQL enum 값 삭제는 테이블 전체 형 변환이 필요하다. 남겨도 구버전 앱과 호환된다.
