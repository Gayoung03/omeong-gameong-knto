"""validate users local requires password check

Revision ID: c7a02c262dc0
Revises: 0a20d1f6a743
Create Date: 2026-08-31 18:30:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "c7a02c262dc0"
down_revision: str | Sequence[str] | None = "0a20d1f6a743"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONSTRAINT_NAME = "ck_users_local_requires_password"


# #6(0a20d1f6a743)에서 NOT VALID 로 추가한 제약을 VALIDATE 한다(ai-io-column-design 8.1-6).
# **선행 조건**: 위반 행(시드 데모 계정)이 0이어야 한다 — dev·프로덕션에서
# `scripts.patch_seed_password` 로 정리한 뒤 이 마이그레이션을 적용한다.
# 위반 행이 남아 있으면 VALIDATE 가 실패해 마이그레이션이 중단된다(안전).
def upgrade() -> None:
    op.execute(f"ALTER TABLE users VALIDATE CONSTRAINT {CONSTRAINT_NAME}")


def downgrade() -> None:
    # no-op. VALIDATE 는 되돌릴 수 없다 — 제약을 다시 NOT VALID 로 만들려면 drop 후
    # 재추가해야 하는데, 그건 #6 의 downgrade 영역이다. 여기서는 아무것도 하지 않는다.
    pass
