"""추천 서비스의 좌표·요청 계약 단위 테스트."""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db.models import Route, RouteDay, RouteItem, RouteRequest, RouteRequestStay
from app.db.models.enums import RouteFailureReason, RouteStatus, ScheduleItemType
from app.integrations.maps.kakao import GeocodedAddress
from app.schemas.route import RouteRequestCreate, RouteRequestStayCreate
from app.services import route_recommendation
from app.services.route_recommendation import (
    RecommendationGenerationError,
    _day_anchors,
    _failure_reason,
    _paired_stay_anchor,
    resolve_location,
)

KST = timezone(timedelta(hours=9))


class FakeSession:
    def __init__(self, place: object | None = None) -> None:
        self.place = place

    def get(self, _model: object, _place_id: uuid.UUID) -> object | None:
        return self.place


class FakeGenerationSession:
    def __init__(self) -> None:
        self.route = SimpleNamespace(
            status=RouteStatus.GENERATING,
            failure_reason=None,
        )
        self.committed = False

    def __enter__(self) -> "FakeGenerationSession":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def rollback(self) -> None:
        pass

    def get(self, _model: object, _route_id: uuid.UUID) -> object:
        return self.route

    def commit(self) -> None:
        self.committed = True


def test_failure_reason_never_uses_internal_exception_message() -> None:
    assert _failure_reason(RuntimeError("SECRET_KEY=do-not-expose")) is RouteFailureReason.UNKNOWN


def test_background_failure_persists_safe_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    db = FakeGenerationSession()

    def fail(*_args: object) -> None:
        raise RecommendationGenerationError(
            "내부 후보 정보",
            RouteFailureReason.NO_RECOMMENDABLE_PLACES,
        )

    monkeypatch.setattr(route_recommendation, "generate_route", fail)

    route_recommendation.run_route_generation(uuid.uuid4(), lambda: db)

    assert db.route.status is RouteStatus.FAILED
    assert db.route.failure_reason is RouteFailureReason.NO_RECOMMENDABLE_PLACES
    assert db.committed is True


def test_resolve_location_prefers_db_place_without_geocoding() -> None:
    db = FakeSession(SimpleNamespace(latitude=33.45, longitude=126.31))

    result = resolve_location(
        db,  # type: ignore[arg-type]
        uuid.uuid4(),
        "호출되면 안 되는 주소",
        geocoder=lambda _address: pytest.fail("DB 장소가 있으면 API를 호출하면 안 됩니다"),
    )

    assert result == (33.45, 126.31)


def test_resolve_location_geocodes_address_without_place_id() -> None:
    result = resolve_location(
        FakeSession(),  # type: ignore[arg-type]
        None,
        "제주시 애월읍",
        geocoder=lambda _address: GeocodedAddress(33.46, 126.31, "제주시 애월읍"),
    )

    assert result == (33.46, 126.31)


def test_stay_requires_db_place_or_address() -> None:
    with pytest.raises(ValidationError, match="placeId 또는 address"):
        RouteRequestStayCreate(name="좌표 없는 숙소")


def test_route_request_accepts_stay_as_start_location() -> None:
    start = datetime(2026, 9, 10, 9, tzinfo=KST)

    payload = RouteRequestCreate(
        start_at=start,
        end_at=start + timedelta(days=1),
        pace="relaxed",
        transport="rental_car",
        stays=[{"name": "애월 숙소", "address": "제주시 애월읍"}],
    )

    assert payload.stays[0].address == "제주시 애월읍"


def test_day_anchors_use_departure_first_and_skip_last_day_return() -> None:
    start = datetime(2026, 9, 10, 9, tzinfo=KST)
    request = RouteRequest(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        start_at=start,
        end_at=start + timedelta(days=2, hours=9),
        departure_location="제주국제공항",
        departure_latitude=Decimal("33.5104"),
        departure_longitude=Decimal("126.4914"),
        pace="relaxed",
        transport="rental_car",
        companion_count=1,
    )
    stay = RouteRequestStay(
        id=uuid.uuid4(),
        route_request_id=request.id,
        name="애월 숙소",
        address="제주시 애월읍",
        latitude=Decimal("33.46"),
        longitude=Decimal("126.31"),
        check_in_at=start.replace(hour=15),
        check_out_at=(start + timedelta(days=2)).replace(hour=11),
    )

    starts, ends = _day_anchors(
        FakeSession(),  # type: ignore[arg-type]
        request,
        [(stay, (33.46, 126.31))],
    )

    assert starts[start.date()].name == "제주국제공항"
    assert starts[(start + timedelta(days=1)).date()].name == "애월 숙소"
    assert ends[start.date()].name == "애월 숙소"
    assert (start + timedelta(days=2)).date() not in ends


def test_arrival_stay_is_paired_with_next_day_departure(db: Session, trip: Route) -> None:
    first_day = trip.route_days[0]
    arrival = first_day.items[-1]
    arrival.item_type = ScheduleItemType.ACCOMMODATION
    second_day = RouteDay(
        id=uuid.uuid4(),
        route_id=trip.id,
        day_number=2,
        route_date=first_day.route_date + timedelta(days=1),
    )
    departure = RouteItem(
        id=uuid.uuid4(),
        route_day_id=second_day.id,
        item_type=ScheduleItemType.ACCOMMODATION,
        custom_place_name="다음 날 출발 숙소",
        sort_order=0,
    )
    db.add_all([second_day, departure])
    db.flush()

    assert _paired_stay_anchor(db, trip, first_day, arrival) == (second_day, departure)
