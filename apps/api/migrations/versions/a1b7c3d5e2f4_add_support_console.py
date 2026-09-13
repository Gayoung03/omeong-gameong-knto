"""add support console: notice announce marker and admin audit logs

Revision ID: a1b7c3d5e2f4
Revises: 6e2a9c4d8f10
Create Date: 2026-09-08 09:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a1b7c3d5e2f4"
down_revision: str | Sequence[str] | None = "6e2a9c4d8f10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _audit_table(name: str, entity_column: str, entity_table: str) -> None:
    op.create_table(
        name,
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(entity_column, sa.UUID(), nullable=False),
        sa.Column("actor_user_id", sa.UUID(), nullable=False),
        sa.Column("action", sa.String(length=30), nullable=False),
        sa.Column("previous_status", sa.String(length=20), nullable=True),
        sa.Column("next_status", sa.String(length=20), nullable=True),
        sa.Column(
            "changes",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["users.id"], name=op.f(f"fk_{name}_actor_users")
        ),
        sa.ForeignKeyConstraint(
            [entity_column],
            [f"{entity_table}.id"],
            name=op.f(f"fk_{name}_{entity_table}"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{name}")),
    )


def upgrade() -> None:
    op.add_column(
        "notices",
        sa.Column("announced_at", sa.DateTime(timezone=True), nullable=True),
    )
    # 기존 공지는 과거에 이미 전 사용자에게 발송됐다. 표식을 채워 두지 않으면
    # 관리자가 옛 공지를 `/publish` 했을 때 전 사용자에게 다시 알림이 간다.
    op.execute("UPDATE notices SET announced_at = published_at")

    _audit_table("admin_inquiry_audit_logs", "inquiry_id", "inquiries")
    op.create_index(
        "ix_admin_inquiry_audit_inquiry_created",
        "admin_inquiry_audit_logs",
        ["inquiry_id", "created_at"],
        unique=False,
    )

    _audit_table("admin_notice_audit_logs", "notice_id", "notices")
    op.create_index(
        "ix_admin_notice_audit_notice_created",
        "admin_notice_audit_logs",
        ["notice_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_admin_notice_audit_notice_created", table_name="admin_notice_audit_logs"
    )
    op.drop_table("admin_notice_audit_logs")
    op.drop_index(
        "ix_admin_inquiry_audit_inquiry_created", table_name="admin_inquiry_audit_logs"
    )
    op.drop_table("admin_inquiry_audit_logs")
    op.drop_column("notices", "announced_at")
