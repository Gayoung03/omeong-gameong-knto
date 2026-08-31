"""add places category_detail

Revision ID: 169d73df0a9f
Revises: 2af6484e68dc
Create Date: 2026-08-31 02:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "169d73df0a9f"
down_revision: str | Sequence[str] | None = "2af6484e68dc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# places.category_detail(ai-io-column-design 7.2·8.1). etc 세부 분류 추출 적재 자리.
# category enum 은 불변(API 계약 보호) — 세분화는 이 nullable 컬럼으로만. 가산적 ADD COLUMN.
def upgrade() -> None:
    op.add_column("places", sa.Column("category_detail", sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column("places", "category_detail")
