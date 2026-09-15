"""add travel_logs.generation_message

Revision ID: a4c7e91b2d63
Revises: f6b3d8a1c2e4

여행기록 카드 생성이 실패한 사유를 **사용자에게 보일 한 줄**로 담는다.

상태(`failed`)만으로는 "다른 사진을 고르라"와 "잠시 후 다시 하라"가 구분되지 않는다.
앞엣것은 같은 사진으로 다시 눌러도 또 실패하는데 재시도 한 번에 카드 한 장 값이
나간다. 사유별 문구는 `integrations/llm/travel_card/agent.py` 의 `MESSAGES` 다.

nullable 이다 — 성공한 기록과 아직 만들지 않은 기록에는 담을 것이 없다.
기존 행은 전부 NULL 로 남고, 앱은 NULL 이면 기본 문구를 쓴다.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a4c7e91b2d63"
down_revision: str | Sequence[str] | None = "f6b3d8a1c2e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("travel_logs", sa.Column("generation_message", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("travel_logs", "generation_message")
