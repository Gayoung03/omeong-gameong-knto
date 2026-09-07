"""backfill applied_weights weather to Phase 5 signal meaning

Revision ID: a1f5c9d3e7b2
Revises: e3c4d5f6a7b8
Create Date: 2026-09-08 16:00:00.000000

Phase 5 에서 weather 점수 축이 0 이 되고 `applied_weights.weather > 0` 가 실내 우선
신호가 됐다. 그 이전 요청 행은 프리셋과 무관하게 weather 가 양수(옛 기본값)라,
재조정(Phase 7 regenerate)이 들어오면 전부 실내 우선이 켜진다. 기존 스냅샷을
새 의미(healing 만 신호, 나머지 0)로 변환하고 6키 합이 1이 되게 재정규화한다.

스키마 변경은 없다. downgrade 는 원래 값을 복원할 수 없어 no-op 다.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.recommend.weights import backfill_weather_signal

revision: str = "a1f5c9d3e7b2"
down_revision: str | Sequence[str] | None = "e3c4d5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


route_requests = sa.table(
    "route_requests",
    sa.column("id", UUID(as_uuid=True)),
    sa.column("priority_preset", sa.String()),
    sa.column("applied_weights", JSONB()),
)


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.select(
            route_requests.c.id,
            route_requests.c.priority_preset,
            route_requests.c.applied_weights,
        ).where(route_requests.c.applied_weights.isnot(None))
    ).all()
    for row in rows:
        new_weights = backfill_weather_signal(row.applied_weights, row.priority_preset)
        bind.execute(
            sa.update(route_requests)
            .where(route_requests.c.id == row.id)
            .values(applied_weights=new_weights)
        )


def downgrade() -> None:
    # 원래 weather 값을 복원할 수 없다(변환이 비가역). 스키마 변경도 없어 no-op.
    pass
