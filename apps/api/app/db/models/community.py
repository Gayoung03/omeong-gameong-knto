"""Favorites, reviews, travel logs, support, notifications, and chat models."""

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import MessageRole, db_enum

if TYPE_CHECKING:
    from app.db.models.users import Pet, User


class Favorite(Base):
    __tablename__ = "favorites"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    place_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("places.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="rating_range"),
        Index("ix_reviews_place_created", "place_id", "created_at"),
        Index("ix_reviews_user_created", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    place_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("places.id", ondelete="CASCADE"), nullable=False
    )
    pet_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pets.id", ondelete="SET NULL")
    )
    rating: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    content: Mapped[str | None] = mapped_column(Text)
    pet_policy_accurate: Mapped[bool | None] = mapped_column(Boolean)
    visited_at: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # --- 파이썬 쪽 연결 -------------------------------------------------
    # ForeignKey(DB 제약)는 이미 있고, 여기서는 파이썬이 그 외래키를 따라가는
    # 통로만 연다. DB 스키마 변경이 아니라서 마이그레이션이 필요 없다.
    images: Mapped[list["ReviewImage"]] = relationship(
        "ReviewImage",
        order_by="ReviewImage.sort_order",
        cascade="all, delete-orphan",
    )
    #: 작성자. 탈퇴(soft delete)해도 행이 남아 있어 None 이 되지는 않는다.
    author: Mapped["User"] = relationship("User")
    #: 함께 간 반려동물. pet_id 가 null 이거나 삭제됐으면 None.
    pet: Mapped["Pet | None"] = relationship("Pet")


class ReviewImage(Base):
    __tablename__ = "review_images"
    __table_args__ = (
        CheckConstraint("sort_order >= 0", name="sort_order_nonnegative"),
        UniqueConstraint("review_id", "sort_order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False
    )
    image_url: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")


class TravelLog(Base):
    __tablename__ = "travel_logs"
    __table_args__ = (
        CheckConstraint(
            "generation_status IN ('idle', 'uploading', 'generating', 'completed', 'failed')",
            name="generation_status_valid",
        ),
        CheckConstraint(
            "writing_style IN ('dog_diary', 'jeju_dialect')", name="writing_style_valid"
        ),
        CheckConstraint(
            "mood IS NULL OR mood IN ('happy', 'excited', 'relaxed', 'bittersweet')",
            name="mood_valid",
        ),
        Index("ix_travel_logs_user_recorded", "user_id", "recorded_date"),
        Index("ix_travel_logs_route_recorded", "route_id", "recorded_date"),
        Index("ix_travel_logs_place_recorded", "place_id", "recorded_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    route_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("routes.id", ondelete="SET NULL")
    )
    place_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("places.id", ondelete="SET NULL")
    )
    place_name_snapshot: Mapped[str] = mapped_column(String(200), nullable=False)
    recorded_date: Mapped[date] = mapped_column(Date, nullable=False)
    visited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    original_image_url: Mapped[str] = mapped_column(Text, nullable=False)
    generated_image_url: Mapped[str | None] = mapped_column(Text)
    writing_style: Mapped[str] = mapped_column(String(30), nullable=False)
    mood: Mapped[str | None] = mapped_column(String(30))
    generation_status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="idle"
    )
    personal_message: Mapped[str | None] = mapped_column(Text)
    is_representative: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    #: 함께한 반려동물의 **스냅샷**. 프로필을 지워도 이름·사진이 남으므로
    #: Pet 이 아니라 TravelLogPet 을 그대로 들고 있는다.
    #: delete-orphan 은 PATCH 가 petIds 를 통째로 갈아끼울 때 필요하다 —
    #: 리스트에서 빼면 파이썬 쪽에서도 행이 지워진다.
    companions: Mapped[list["TravelLogPet"]] = relationship(
        "TravelLogPet",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class TravelLogPet(Base):
    __tablename__ = "travel_log_pets"
    __table_args__ = (UniqueConstraint("travel_log_id", "pet_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    travel_log_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("travel_logs.id", ondelete="CASCADE"), nullable=False
    )
    pet_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pets.id", ondelete="SET NULL")
    )
    pet_name_snapshot: Mapped[str] = mapped_column(String(50), nullable=False)
    pet_profile_image_snapshot: Mapped[str | None] = mapped_column(Text)


class Inquiry(Base):
    __tablename__ = "inquiries"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'completed')", name="status_valid"),
        CheckConstraint(
            "status <> 'completed' OR (answer IS NOT NULL AND answered_at IS NOT NULL)",
            name="completed_has_answer",
        ),
        Index("ix_inquiries_user_status_created", "user_id", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pending")
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    image_urls: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    answer: Mapped[str | None] = mapped_column(Text)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class Notice(Base):
    __tablename__ = "notices"
    __table_args__ = (
        Index("ix_notices_active_pinned_published", "is_active", "is_pinned", "published_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint("is_read = false OR read_at IS NOT NULL", name="read_has_timestamp"),
        Index("ix_notifications_user_read_created", "user_id", "is_read", "created_at"),
        Index("ix_notifications_user_created", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    icon_key: Mapped[str | None] = mapped_column(String(50))
    action_path: Mapped[str | None] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ChatConversation(Base):
    __tablename__ = "chat_conversations"
    __table_args__ = (Index("ix_chat_conversations_user_updated", "user_id", "updated_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    route_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("routes.id", ondelete="SET NULL")
    )
    title: Mapped[str | None] = mapped_column(String(150))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        Index("ix_chat_messages_conversation_created", "conversation_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chat_conversations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[MessageRole] = mapped_column(db_enum(MessageRole, "message_role"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    referenced_place_ids: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(UUID(as_uuid=True)))
    model_name: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
