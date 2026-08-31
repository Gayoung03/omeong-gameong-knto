"""add places business hours and stay times

Revision ID: 16d96164ba8a
Revises: 169d73df0a9f
Create Date: 2026-08-31 15:51:40.689090
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "16d96164ba8a"
down_revision: str | Sequence[str] | None = "169d73df0a9f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# places 영업·숙박 3컬럼(ai-io-column-design 7.3·8.1). 전부 nullable, 가산적 ADD COLUMN.
# business_hours_raw 는 place_business_hours.raw_text 이관 목적지(드롭은 별도·최후 마이그레이션).
# check_in/out 은 숙박 시간 분리용 신규 필드 — 시간 쌍 강제 CHECK 는 두지 않는다.
def upgrade() -> None:
    op.add_column("places", sa.Column("business_hours_raw", sa.Text(), nullable=True))
    op.add_column("places", sa.Column("check_in_time", sa.Time(), nullable=True))
    op.add_column("places", sa.Column("check_out_time", sa.Time(), nullable=True))


def downgrade() -> None:
    op.drop_column("places", "check_out_time")
    op.drop_column("places", "check_in_time")
    op.drop_column("places", "business_hours_raw")
