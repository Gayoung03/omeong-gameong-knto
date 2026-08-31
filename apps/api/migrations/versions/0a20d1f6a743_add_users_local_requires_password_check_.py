"""add users local requires password check not valid

Revision ID: 0a20d1f6a743
Revises: 4f56f1e397bf
Create Date: 2026-08-31 17:10:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0a20d1f6a743"
down_revision: str | Sequence[str] | None = "4f56f1e397bf"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONSTRAINT_NAME = "ck_users_local_requires_password"


# users: local(이메일) 계정은 password_hash 필수(ai-io-column-design 7.8·8.1-6).
#
# **NOT VALID 로 추가한다** — 기존 행을 스캔하지 않아 위반 행(시드 데모 계정)이 있어도
# 마이그레이션이 실패하지 않고, 신규/수정 행부터 즉시 강제된다. 실 local 가입자는 이미
# password_hash 가 있어 영향 없다.
#
# VALIDATE 는 이 마이그레이션에 넣지 않는다. dev·프로덕션 시드 계정 해시를 채워
# 위반 0을 확인한 뒤 별도 마이그레이션(#6b)에서 `VALIDATE CONSTRAINT` 한다.
def upgrade() -> None:
    op.execute(
        "ALTER TABLE users ADD CONSTRAINT "
        f"{CONSTRAINT_NAME} CHECK "
        "(auth_provider <> 'local' OR password_hash IS NOT NULL) NOT VALID"
    )


def downgrade() -> None:
    # op.f 로 최종 이름 그대로 드롭한다(감싸지 않으면 naming_convention 이 ck_users_ 를 또 붙인다).
    op.drop_constraint(op.f(CONSTRAINT_NAME), "users", type_="check")
