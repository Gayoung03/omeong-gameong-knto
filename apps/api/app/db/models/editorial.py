"""관리자 검수 전제를 가진 제주 여행 이야기 모델."""

import uuid
from datetime import datetime

from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.enums import EditorialStoryKind, EditorialStoryStatus, db_enum


class EditorialStory(Base):
    __tablename__ = "editorial_stories"
    __table_args__ = (
        Index("ix_editorial_stories_status_published", "status", "published_at"),
        Index("ix_editorial_stories_kind_published", "kind", "published_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    kind: Mapped[EditorialStoryKind] = mapped_column(
        db_enum(EditorialStoryKind, "editorial_story_kind"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    card_title: Mapped[str] = mapped_column(String(160), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    hero_image_url: Mapped[str] = mapped_column(Text, nullable=False)
    sections: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)
    tips: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String(50)), nullable=False, default=list)
    status: Mapped[EditorialStoryStatus] = mapped_column(
        db_enum(EditorialStoryStatus, "editorial_story_status"),
        nullable=False,
        server_default="draft",
    )
    display_order: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("0")
    )
    generated_by_ai: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    generation_model: Mapped[str | None] = mapped_column(String(80))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class EditorialStorySource(Base):
    """초안의 근거. 수집 원문은 저장하지 않고 공식 링크와 식별자만 남긴다."""

    __tablename__ = "editorial_story_sources"
    __table_args__ = (
        UniqueConstraint(
            "story_id",
            "provider",
            "external_id",
            name="uq_editorial_story_source_identity",
        ),
        Index("ix_editorial_story_sources_story_id", "story_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    story_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("editorial_stories.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    external_id: Mapped[str] = mapped_column(String(160), nullable=False)
    source_name: Mapped[str] = mapped_column(String(120), nullable=False)
    source_title: Mapped[str] = mapped_column(String(300), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_image_url: Mapped[str | None] = mapped_column(Text)
    source_published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
