"""Place catalog, source mapping, policy, and tag models."""

import uuid
from datetime import datetime, time
from decimal import Decimal

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.enums import DataProvider, PetPolicyType, PlaceEnvironment, db_enum


class Place(Base):
    __tablename__ = "places"
    __table_args__ = (
        CheckConstraint("latitude BETWEEN -90 AND 90", name="latitude_range"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="longitude_range"),
        Index("ix_places_latitude_longitude", "latitude", "longitude"),
        Index("ix_places_category", "category"),
        Index("ix_places_region", "region"),
        Index("ix_places_created_by_user_id", "created_by_user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    # etc 세부 분류(동물약국·동물병원 등)를 description 에서 추출해 담는 자리.
    # category enum 은 불변(API 계약 보호) — 세분화는 이 컬럼으로만. 값은 파싱 배치가 채운다.
    category_detail: Mapped[str | None] = mapped_column(String(50))
    region: Mapped[str | None] = mapped_column(String(50))
    address: Mapped[str | None] = mapped_column(Text)
    road_address: Mapped[str | None] = mapped_column(Text)
    latitude: Mapped[Decimal] = mapped_column(Numeric(10, 7), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(10, 7), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50))
    homepage_url: Mapped[str | None] = mapped_column(Text)
    primary_image_url: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    description_source: Mapped[DataProvider | None] = mapped_column(
        db_enum(DataProvider, "data_provider")
    )
    environment: Mapped[PlaceEnvironment | None] = mapped_column(
        db_enum(PlaceEnvironment, "place_environment")
    )
    amenities: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    average_stay_minutes: Mapped[int | None] = mapped_column(Integer)
    reservation_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class PlaceExternalRef(Base):
    __tablename__ = "place_external_refs"
    __table_args__ = (
        UniqueConstraint("provider", "external_id"),
        Index("ix_place_external_refs_place_provider", "place_id", "provider"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    place_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("places.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[DataProvider] = mapped_column(
        db_enum(DataProvider, "data_provider"), nullable=False
    )
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PlaceBusinessHour(Base):
    __tablename__ = "place_business_hours"
    __table_args__ = (
        UniqueConstraint("place_id", "day_of_week"),
        CheckConstraint("day_of_week BETWEEN 0 AND 6", name="day_of_week_range"),
        CheckConstraint(
            "(break_start_at IS NULL) = (break_end_at IS NULL)",
            name="break_pair_complete",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    place_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("places.id", ondelete="CASCADE"), nullable=False
    )
    day_of_week: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    opens_at: Mapped[time | None] = mapped_column(Time)
    closes_at: Mapped[time | None] = mapped_column(Time)
    break_start_at: Mapped[time | None] = mapped_column(Time)
    break_end_at: Mapped[time | None] = mapped_column(Time)
    is_closed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    raw_text: Mapped[str | None] = mapped_column(Text)


class PlacePetPolicy(Base):
    __tablename__ = "place_pet_policies"
    __table_args__ = (
        CheckConstraint(
            "max_weight_kg IS NULL OR max_weight_kg >= 0", name="max_weight_nonnegative"
        ),
        CheckConstraint(
            "extra_fee_amount IS NULL OR extra_fee_amount >= 0", name="extra_fee_nonnegative"
        ),
        CheckConstraint(
            "reliability_score IS NULL OR reliability_score BETWEEN 0 AND 100",
            name="reliability_score_range",
        ),
        CheckConstraint(
            "max_pets_per_person IS NULL OR max_pets_per_person >= 1",
            name="max_pets_per_person_positive",
        ),
        Index("ix_place_pet_policies_place_id", "place_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    place_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("places.id", ondelete="CASCADE"), nullable=False
    )
    policy_type: Mapped[PetPolicyType] = mapped_column(
        db_enum(PetPolicyType, "pet_policy_type"), nullable=False, server_default="unknown"
    )
    allowed_species: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    allowed_sizes: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    max_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    carrier_required: Mapped[bool | None] = mapped_column(Boolean)
    leash_required: Mapped[bool | None] = mapped_column(Boolean)
    vaccination_required: Mapped[bool | None] = mapped_column(Boolean)
    extra_fee_amount: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    source: Mapped[DataProvider] = mapped_column(
        db_enum(DataProvider, "data_provider"), nullable=False
    )
    source_url: Mapped[str | None] = mapped_column(Text)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reliability_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    # AI 입출력 컬럼(ai-io-column-design 7.1). 전부 nullable — 3값 의미 유지
    # (True/False = 명시, NULL = 미확인). notes 파싱 배치가 채운다.
    muzzle_required: Mapped[bool | None] = mapped_column(Boolean)  # 입마개 필수 여부
    food_area_allowed: Mapped[bool | None] = mapped_column(Boolean)  # 식음료 공간 동반 가능
    max_pets_per_person: Mapped[int | None] = mapped_column(SmallInteger)  # 1인당 동반 마리수 상한
    # 정제된 주의사항. 원본 notes 는 그대로 두고(AI 등급 X) 이 컬럼만 관찰에 쓴다.
    caution_note: Mapped[str | None] = mapped_column(String(150))


class PlaceTag(Base):
    __tablename__ = "place_tags"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)


class PlaceTagLink(Base):
    __tablename__ = "place_tag_links"
    __table_args__ = (
        CheckConstraint(
            "confidence IS NULL OR confidence BETWEEN 0 AND 1", name="confidence_range"
        ),
    )

    place_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("places.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("place_tags.id", ondelete="CASCADE"), primary_key=True
    )
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    source: Mapped[DataProvider] = mapped_column(
        db_enum(DataProvider, "data_provider"), nullable=False
    )
