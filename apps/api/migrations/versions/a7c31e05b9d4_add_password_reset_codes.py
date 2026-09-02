"""add password reset codes and users.password_changed_at

Revision ID: a7c31e05b9d4
Revises: f3a9c1d47b02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a7c31e05b9d4"
down_revision: str | Sequence[str] | None = "f3a9c1d47b02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 기존 계정은 NULL 로 남는다 — "한 번도 바꾼 적 없음" 이라 아무 토큰도 무효화하지
    # 않는다. 여기에 now() 를 채우면 배포 순간 전원이 로그아웃된다.
    op.add_column(
        "users", sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True)
    )

    op.create_table(
        "password_reset_codes",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("code_hash", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index(
        "ix_password_reset_codes_user_created", "password_reset_codes", ["user_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_password_reset_codes_user_created", table_name="password_reset_codes")
    op.drop_table("password_reset_codes")
    op.drop_column("users", "password_changed_at")
