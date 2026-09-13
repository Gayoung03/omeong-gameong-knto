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

revision: str = "a1f5c9d3e7b2"
down_revision: str | Sequence[str] | None = "e3c4d5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# healing 프리셋이 남기는 weather 신호값. app.recommend.config.weights.WEATHER_SIGNAL_WEIGHT
# 과 동일하지만, 마이그레이션 자족성(미래 앱 코드 변경과 무관한 재현)을 위해 복사한다.
_WEATHER_SIGNAL_WEIGHT = 0.10


route_requests = sa.table(
    "route_requests",
    sa.column("id", UUID(as_uuid=True)),
    sa.column("priority_preset", sa.String()),
    sa.column("applied_weights", JSONB()),
)


def _backfill_weather_signal(
    applied_weights: dict[str, float], priority_preset: str | None
) -> dict[str, float]:
    """app.recommend.weights.backfill_weather_signal 과 동일 — 마이그레이션 자족성을 위해 복사.

    healing 이면 weather 를 신호값으로, 아니면 0 으로 두고 6키 합이 1이 되게 재정규화한다.
    """
    resolved = dict(applied_weights)
    resolved["weather"] = _WEATHER_SIGNAL_WEIGHT if priority_preset == "healing" else 0.0
    total = sum(resolved.values())
    if total <= 0:
        return resolved
    return {key: value / total for key, value in resolved.items()}


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
        new_weights = _backfill_weather_signal(row.applied_weights, row.priority_preset)
        bind.execute(
            sa.update(route_requests)
            .where(route_requests.c.id == row.id)
            .values(applied_weights=new_weights)
        )


def downgrade() -> None:
    # 원래 weather 값을 복원할 수 없다(변환이 비가역). 스키마 변경도 없어 no-op.
    pass
