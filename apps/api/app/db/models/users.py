"""User, pet, and default travel preference models."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.enums import (
    AuthProvider,
    ConsentType,
    PetSize,
    PetSpecies,
    TransportType,
    TripPace,
    db_enum,
)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("auth_provider", "provider_user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    auth_provider: Mapped[AuthProvider] = mapped_column(
        db_enum(AuthProvider, "auth_provider"), nullable=False, server_default="local"
    )
    provider_user_id: Mapped[str | None] = mapped_column(String(255))
    nickname: Mapped[str] = mapped_column(String(50), nullable=False)
    profile_image_url: Mapped[str | None] = mapped_column(Text)
    inquiry_answer_notification_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    marketing_notification_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class UserConsent(Base):
    """약관 동의 이력.

    한 행을 고쳐 쓰지 않고 동의·철회가 있을 때마다 새 행을 쌓는다.
    마케팅 동의는 켜고 끌 수 있고 약관은 개정될 수 있어서, 덮어쓰면
    "그 시점에 어떤 버전에 동의했는지"가 사라져 분쟁 시 증빙이 되지 않는다.

    현재 동의 상태는 (user_id, consent_type)별 created_at 이 가장 큰 행이다.
    """

    __tablename__ = "user_consents"
    __table_args__ = (
        Index("ix_user_consents_user_type_created", "user_id", "consent_type", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    consent_type: Mapped[ConsentType] = mapped_column(
        db_enum(ConsentType, "consent_type"), nullable=False
    )
    #: 동의는 True, 철회는 False.
    is_agreed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    #: 동의한 약관 문서의 버전. 문서가 없는 age_14_or_over 는 비어 있다.
    document_version: Mapped[str | None] = mapped_column(String(50))
    #: 동의하거나 철회한 시각.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Pet(Base):
    __tablename__ = "pets"
    __table_args__ = (
        CheckConstraint("weight_kg IS NULL OR weight_kg >= 0", name="weight_nonnegative"),
        CheckConstraint(
            "(species = 'other' AND species_detail IS NOT NULL "
            "AND btrim(species_detail) <> '') "
            "OR (species <> 'other' AND species_detail IS NULL)",
            name="species_detail_consistency",
        ),
        Index(
            "uq_pets_user_primary_active",
            "user_id",
            unique=True,
            postgresql_where=text("is_primary = true AND deleted_at IS NULL"),
        ),
        Index("ix_pets_user_active", "user_id", "deleted_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    species: Mapped[PetSpecies] = mapped_column(db_enum(PetSpecies, "pet_species"), nullable=False)
    species_detail: Mapped[str | None] = mapped_column(String(50))
    breed: Mapped[str | None] = mapped_column(String(100))
    size: Mapped[PetSize | None] = mapped_column(db_enum(PetSize, "pet_size"))
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    birth_date: Mapped[date | None] = mapped_column(Date)
    image_url: Mapped[str | None] = mapped_column(Text)
    health_notes: Mapped[str | None] = mapped_column(Text)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class UserTravelPreference(Base):
    __tablename__ = "user_travel_preferences"
    __table_args__ = (
        CheckConstraint(
            "preferred_duration_days IS NULL OR preferred_duration_days >= 1",
            name="duration_positive",
        ),
        CheckConstraint("companion_count >= 1", name="companion_count_positive"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    default_pace: Mapped[TripPace | None] = mapped_column(db_enum(TripPace, "trip_pace"))
    default_transport: Mapped[TransportType | None] = mapped_column(
        db_enum(TransportType, "transport_type")
    )
    departure_location: Mapped[str | None] = mapped_column(String(100))
    preferred_duration_days: Mapped[int | None] = mapped_column(Integer)
    companion_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    preferred_tags: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class UserSocialAccount(Base):
    """소셜 로그인 수단 연결 (docs/api/auth.md 소셜 절).

    `users.auth_provider` 컬럼은 하나라 "이메일 계정 + 카카오 연동" 같은 다중 수단을
    표현할 수 없어 이 연결 테이블이 필요하다. `users.auth_provider`·`provider_user_id`
    는 "최초 가입 수단" 기록으로 의미를 고정하고, 로그인 판정은 여기의
    `(provider, provider_user_id)` UNIQUE 로 한다.
    """

    __tablename__ = "user_social_accounts"
    __table_args__ = (
        # local 은 소셜 수단이 아니다 — 이 테이블에 들어오면 안 된다.
        CheckConstraint("provider <> 'local'", name="social_provider_not_local"),
        UniqueConstraint("provider", "provider_user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[AuthProvider] = mapped_column(
        db_enum(AuthProvider, "auth_provider"), nullable=False
    )
    provider_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    linked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
