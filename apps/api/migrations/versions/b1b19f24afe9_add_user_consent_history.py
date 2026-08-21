"""add user consent history

Revision ID: b1b19f24afe9
Revises: 8c71f4a2d9e0
Create Date: 2026-08-21 15:26:18.650219
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b1b19f24afe9"
down_revision: str | Sequence[str] | None = "8c71f4a2d9e0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


consent_type = postgresql.ENUM(
    "terms_of_service",
    "privacy_policy",
    "age_14_or_over",
    "marketing",
    name="consent_type",
    create_type=False,
)


def upgrade() -> None:
    consent_type.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "user_consents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("consent_type", consent_type, nullable=False),
        sa.Column("is_agreed", sa.Boolean(), nullable=False),
        sa.Column("document_version", sa.String(length=50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_user_consents_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_consents")),
    )
    op.create_index(
        "ix_user_consents_user_type_created",
        "user_consents",
        ["user_id", "consent_type", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_user_consents_user_type_created", table_name="user_consents")
    op.drop_table("user_consents")
    consent_type.drop(op.get_bind(), checkfirst=True)
