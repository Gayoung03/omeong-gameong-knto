"""add editorial stories

Revision ID: d8f4a21c9b70
Revises: b5e07c19af23
Create Date: 2026-09-06 13:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d8f4a21c9b70"
down_revision: str | Sequence[str] | None = "b5e07c19af23"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "editorial_stories",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("event", "weather", "story", "guide", name="editorial_story_kind"),
            nullable=False,
        ),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("card_title", sa.String(length=160), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("hero_image_url", sa.Text(), nullable=False),
        sa.Column("sections", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("tips", postgresql.ARRAY(sa.Text()), server_default="{}", nullable=False),
        sa.Column(
            "tags", postgresql.ARRAY(sa.String(length=50)), server_default="{}", nullable=False
        ),
        sa.Column(
            "status",
            sa.Enum("draft", "published", "archived", name="editorial_story_status"),
            server_default="draft",
            nullable=False,
        ),
        sa.Column("display_order", sa.SmallInteger(), server_default="0", nullable=False),
        sa.Column("generated_by_ai", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("generation_model", sa.String(length=80), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_editorial_stories")),
        sa.UniqueConstraint("slug", name=op.f("uq_editorial_stories_slug")),
    )
    op.create_index(
        "ix_editorial_stories_kind_published",
        "editorial_stories",
        ["kind", "published_at"],
        unique=False,
    )
    op.create_index(
        "ix_editorial_stories_status_published",
        "editorial_stories",
        ["status", "published_at"],
        unique=False,
    )
    op.create_table(
        "editorial_story_sources",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("story_id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("external_id", sa.String(length=160), nullable=False),
        sa.Column("source_name", sa.String(length=120), nullable=False),
        sa.Column("source_title", sa.String(length=300), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_image_url", sa.Text(), nullable=True),
        sa.Column("source_published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "collected_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["story_id"],
            ["editorial_stories.id"],
            name=op.f("fk_editorial_story_sources_story_id_editorial_stories"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_editorial_story_sources")),
        sa.UniqueConstraint(
            "story_id", "provider", "external_id", name="uq_editorial_story_source_identity"
        ),
    )
    op.create_index(
        "ix_editorial_story_sources_story_id",
        "editorial_story_sources",
        ["story_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_editorial_story_sources_story_id", table_name="editorial_story_sources")
    op.drop_table("editorial_story_sources")
    op.drop_index("ix_editorial_stories_status_published", table_name="editorial_stories")
    op.drop_index("ix_editorial_stories_kind_published", table_name="editorial_stories")
    op.drop_table("editorial_stories")
    sa.Enum(name="editorial_story_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="editorial_story_kind").drop(op.get_bind(), checkfirst=True)
