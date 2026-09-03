"""add chat conversation deleted_at

Revision ID: b5e07c19af23
Revises: a7c31e05b9d4
Create Date: 2026-09-03 18:05:00.000000

대화를 지워도 `chat_messages` 는 남긴다. 목록에서만 빼고, 휴지통에서 되살릴 수 있게
`deleted_at` 만 채운다(users·pets 와 같은 방식).

기존 행은 전부 NULL(= 살아 있음)이라 데이터 이관이 없다.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b5e07c19af23"
down_revision: str | Sequence[str] | None = "a7c31e05b9d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDEX_NAME = "ix_chat_conversations_user_updated"


def upgrade() -> None:
    op.add_column(
        "chat_conversations",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    # 목록 조회는 언제나 `deleted_at IS NULL` 을 끼고 돈다. 인덱스를 조건부로 다시
    # 만들어 지운 대화가 인덱스 자리를 차지하지 않게 한다(pets 의 ix_pets_user_active
    # 와 같은 방식). 이름을 그대로 두므로 앱 쪽 이름 참조는 바뀌지 않는다.
    op.drop_index(INDEX_NAME, table_name="chat_conversations")
    op.create_index(
        INDEX_NAME,
        "chat_conversations",
        ["user_id", "updated_at"],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    # 인덱스를 먼저 되돌린다 — 조건에 deleted_at 이 걸려 있어 컬럼보다 뒤에 지우면
    # 의존성 때문에 실패한다.
    op.drop_index(INDEX_NAME, table_name="chat_conversations")
    op.create_index(
        INDEX_NAME,
        "chat_conversations",
        ["user_id", "updated_at"],
        unique=False,
    )
    op.drop_column("chat_conversations", "deleted_at")
