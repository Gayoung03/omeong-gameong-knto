"""add user social accounts

Revision ID: 83e31e2be855
Revises: 31a78f4d2c9b
Create Date: 2026-08-29 14:30:38.824939
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "83e31e2be855"
down_revision: str | Sequence[str] | None = "31a78f4d2c9b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# auth_provider enum 은 users 테이블이 이미 쓰고 있어 여기서 새로 만들지 않는다.
# create_type=False — 존재하는 타입을 참조만 한다(중복 CREATE TYPE 방지).
auth_provider = postgresql.ENUM(
    "local",
    "kakao",
    "apple",
    "google",
    name="auth_provider",
    create_type=False,
)


def upgrade() -> None:
    op.create_table(
        "user_social_accounts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("provider", auth_provider, nullable=False),
        sa.Column("provider_user_id", sa.String(length=255), nullable=False),
        sa.Column(
            "linked_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "provider <> 'local'",
            name=op.f("ck_user_social_accounts_social_provider_not_local"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_user_social_accounts_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_social_accounts")),
        sa.UniqueConstraint(
            "provider",
            "provider_user_id",
            name=op.f("uq_user_social_accounts_provider_provider_user_id"),
        ),
    )


def downgrade() -> None:
    op.drop_table("user_social_accounts")
