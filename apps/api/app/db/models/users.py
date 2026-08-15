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
