"""Route request, recommendation, schedule, weather, and trip utility models."""

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
    SmallInteger,
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
    RouteStatus,
    ScheduleItemType,
    TransportType,
    TripPace,
    WeatherCondition,
    db_enum,
)


class RouteRequest(Base):
    __tablename__ = "route_requests"
    __table_args__ = (
        CheckConstraint("end_at > start_at", name="date_order"),
        CheckConstraint("companion_count >= 1", name="companion_count_positive"),
        Index("ix_route_requests_user_created", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str | None] = mapped_column(String(150))
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    departure_location: Mapped[str | None] = mapped_column(String(100))
    departure_place_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("places.id", ondelete="SET NULL")
    )
    pace: Mapped[TripPace] = mapped_column(db_enum(TripPace, "trip_pace"), nullable=False)
    transport: Mapped[TransportType] = mapped_column(
        db_enum(TransportType, "transport_type"), nullable=False
    )
    companion_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    preferred_tags: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    request_text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class RouteRequestPet(Base):
    __tablename__ = "route_request_pets"

    route_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("route_requests.id", ondelete="CASCADE"),
        primary_key=True,
    )
    pet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pets.id", ondelete="RESTRICT"), primary_key=True
    )


class RouteRequestStay(Base):
    __tablename__ = "route_request_stays"
    __table_args__ = (
        CheckConstraint(
            "check_out_at IS NULL OR check_in_at IS NULL OR check_out_at > check_in_at",
            name="date_order",
        ),
        Index("ix_route_request_stays_request", "route_request_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    route_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("route_requests.id", ondelete="CASCADE"), nullable=False
    )
    place_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("places.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[str | None] = mapped_column(Text)
    check_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    check_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Route(Base):
    __tablename__ = "routes"
    __table_args__ = (
        UniqueConstraint("route_request_id", "version"),
        CheckConstraint("end_at > start_at", name="date_order"),
        CheckConstraint("version >= 1", name="version_positive"),
        Index("ix_routes_user_status", "user_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    route_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("route_requests.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    status: Mapped[RouteStatus] = mapped_column(
        db_enum(RouteStatus, "route_status"), nullable=False, server_default="generating"
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    pace: Mapped[TripPace] = mapped_column(db_enum(TripPace, "trip_pace"), nullable=False)
    transport: Mapped[TransportType] = mapped_column(
        db_enum(TransportType, "transport_type"), nullable=False
    )
    explanation: Mapped[str | None] = mapped_column(Text)
    total_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    pet_safety_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    cover_image_url: Mapped[str | None] = mapped_column(Text)
    style_keywords: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    memo: Mapped[str | None] = mapped_column(Text)
    share_token: Mapped[str | None] = mapped_column(String(100), unique=True)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class WeatherSnapshot(Base):
    __tablename__ = "weather_snapshots"
    __table_args__ = (
        UniqueConstraint("region", "forecast_at"),
        CheckConstraint("latitude IS NULL OR latitude BETWEEN -90 AND 90", name="latitude_range"),
        CheckConstraint(
            "longitude IS NULL OR longitude BETWEEN -180 AND 180", name="longitude_range"
        ),
        CheckConstraint(
            "precipitation_probability IS NULL OR precipitation_probability BETWEEN 0 AND 100",
            name="precipitation_range",
        ),
        CheckConstraint("humidity IS NULL OR humidity BETWEEN 0 AND 100", name="humidity_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    region: Mapped[str] = mapped_column(String(50), nullable=False)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    forecast_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    condition: Mapped[WeatherCondition] = mapped_column(
        db_enum(WeatherCondition, "weather_condition"), nullable=False
    )
    temperature: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    min_temperature: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    max_temperature: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    precipitation_probability: Mapped[int | None] = mapped_column(SmallInteger)
    humidity: Mapped[int | None] = mapped_column(SmallInteger)
    wind_speed: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    source_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RouteDay(Base):
    __tablename__ = "route_days"
    __table_args__ = (
        UniqueConstraint("route_id", "day_number"),
        CheckConstraint("day_number >= 1", name="day_number_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    route_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("routes.id", ondelete="CASCADE"), nullable=False
    )
    day_number: Mapped[int] = mapped_column(Integer, nullable=False)
    route_date: Mapped[date] = mapped_column(Date, nullable=False)
    weather_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("weather_snapshots.id", ondelete="SET NULL")
    )
    title: Mapped[str | None] = mapped_column(String(150))


class RouteItem(Base):
    __tablename__ = "route_items"
    __table_args__ = (
        UniqueConstraint("route_day_id", "sort_order"),
        CheckConstraint("sort_order >= 0", name="sort_order_nonnegative"),
        CheckConstraint(
            "ends_at IS NULL OR starts_at IS NULL OR ends_at > starts_at", name="date_order"
        ),
        CheckConstraint("stay_minutes IS NULL OR stay_minutes >= 0", name="stay_nonnegative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    route_day_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("route_days.id", ondelete="CASCADE"), nullable=False
    )
    place_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("places.id", ondelete="SET NULL")
    )
    custom_place_name: Mapped[str | None] = mapped_column(String(200))
    item_type: Mapped[ScheduleItemType] = mapped_column(
        db_enum(ScheduleItemType, "schedule_item_type"), nullable=False
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    stay_minutes: Mapped[int | None] = mapped_column(Integer)
    note: Mapped[str | None] = mapped_column(Text)
    recommendation_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    recommendation_reason: Mapped[str | None] = mapped_column(Text)
    is_selected: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))


class RouteMove(Base):
    __tablename__ = "route_moves"
    __table_args__ = (
        CheckConstraint("from_item_id <> to_item_id", name="different_items"),
        UniqueConstraint("from_item_id", "to_item_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    from_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("route_items.id", ondelete="CASCADE"), nullable=False
    )
    to_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("route_items.id", ondelete="CASCADE"), nullable=False
    )
    transport: Mapped[TransportType] = mapped_column(
        db_enum(TransportType, "transport_type"), nullable=False
    )


class RouteCalculationCache(Base):
    __tablename__ = "route_calculation_cache"
    __table_args__ = (
        CheckConstraint("origin_latitude BETWEEN -90 AND 90", name="origin_latitude_range"),
        CheckConstraint("origin_longitude BETWEEN -180 AND 180", name="origin_longitude_range"),
        CheckConstraint(
            "destination_latitude BETWEEN -90 AND 90", name="destination_latitude_range"
        ),
        CheckConstraint(
            "destination_longitude BETWEEN -180 AND 180", name="destination_longitude_range"
        ),
        CheckConstraint("distance_meters >= 0", name="distance_nonnegative"),
        CheckConstraint("duration_minutes >= 0", name="duration_nonnegative"),
        CheckConstraint("expires_at > calculated_at", name="expiry_order"),
        Index("ix_route_calculation_cache_expires_at", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    origin_latitude: Mapped[Decimal] = mapped_column(Numeric(10, 7), nullable=False)
    origin_longitude: Mapped[Decimal] = mapped_column(Numeric(10, 7), nullable=False)
    destination_latitude: Mapped[Decimal] = mapped_column(Numeric(10, 7), nullable=False)
    destination_longitude: Mapped[Decimal] = mapped_column(Numeric(10, 7), nullable=False)
    transport: Mapped[TransportType] = mapped_column(
        db_enum(TransportType, "transport_type"), nullable=False
    )
    requested_departure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    distance_meters: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    polyline: Mapped[str | None] = mapped_column(Text)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RouteChecklistItem(Base):
    __tablename__ = "route_checklist_items"
    __table_args__ = (
        CheckConstraint("sort_order >= 0", name="sort_order_nonnegative"),
        Index("ix_route_checklist_items_route_category", "route_id", "category"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    route_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("routes.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    is_checked: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    is_recommended: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")


class RouteMemo(Base):
    __tablename__ = "route_memos"
    __table_args__ = (Index("ix_route_memos_route_day", "route_id", "route_day_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    route_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("routes.id", ondelete="CASCADE"), nullable=False
    )
    route_day_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("route_days.id", ondelete="CASCADE")
    )
    title: Mapped[str | None] = mapped_column(String(150))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
