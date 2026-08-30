"""추천 서비스의 좌표·요청 계약 단위 테스트."""

import uuid
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db.models import Route, RouteDay, RouteItem, RouteRequest, RouteRequestStay
from app.db.models.enums import ScheduleItemType, TransportType, TripPace
from app.integrations.maps.kakao import GeocodedAddress
from app.recommend.tmap import RouteLeg, TMapError
from app.schemas.route import RouteRequestCreate, RouteRequestStayCreate
from app.services.route_recommendation import (
    _cascade_item_times,
    _day_anchors,
    _fit_edited_item_visit,
    _paired_stay_anchor,
    resolve_location,
)

KST = timezone(timedelta(hours=9))


class FakeSession:
    def __init__(self, place: object | None = None, scalar_result: object | None = None) -> None:
        self.place = place
        self.scalar_result = scalar_result
        self.flushed = False

    def get(self, _model: object, _place_id: uuid.UUID) -> object | None:
        return self.place

    def scalar(self, _statement: object) -> object | None:
        return self.scalar_result

    def flush(self) -> None:
        self.flushed = True


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


def test_cascade_uses_departure_after_rest_for_route_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = datetime(2026, 9, 10, 10, tzinfo=KST)
    requested_departures: list[datetime] = []

    def fake_route(*args: object) -> RouteLeg:
        requested_departures.append(args[4])  # type: ignore[arg-type]
        return RouteLeg(distance_m=1_000, duration_min=20, polyline=None)

    monkeypatch.setattr("app.services.route_recommendation.get_route", fake_route)
    db = FakeSession()
    route = SimpleNamespace(
        pace=TripPace.NORMAL,
        transport=TransportType.RENTAL_CAR,
        end_at=datetime(2026, 9, 10, 22, tzinfo=KST),
    )
    item = SimpleNamespace(
        place_id=None,
        latitude=Decimal("33.45"),
        longitude=Decimal("126.31"),
        stay_minutes=60,
        starts_at=None,
        ends_at=None,
    )

    _cascade_item_times(
        db,  # type: ignore[arg-type]
        route,  # type: ignore[arg-type]
        current,
        (33.40, 126.20),
        [item],
    )

    assert requested_departures == [current + timedelta(minutes=25)]
    assert item.starts_at == current + timedelta(minutes=45)
    assert item.ends_at == current + timedelta(minutes=105)


def test_cascade_clears_remaining_times_when_tmap_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_route(*_args: object) -> RouteLeg:
        raise TMapError("temporary failure")

    monkeypatch.setattr("app.services.route_recommendation.get_route", fail_route)
    db = FakeSession()
    route = SimpleNamespace(
        pace=TripPace.NORMAL,
        transport=TransportType.RENTAL_CAR,
        end_at=datetime(2026, 9, 10, 22, tzinfo=KST),
    )
    items = [
        SimpleNamespace(
            place_id=None,
            latitude=Decimal("33.45"),
            longitude=Decimal("126.31"),
            stay_minutes=60,
            starts_at=datetime(2026, 9, 10, 12, tzinfo=KST),
            ends_at=datetime(2026, 9, 10, 13, tzinfo=KST),
        ),
        SimpleNamespace(
            place_id=None,
            latitude=Decimal("33.46"),
            longitude=Decimal("126.32"),
            stay_minutes=30,
            starts_at=datetime(2026, 9, 10, 14, tzinfo=KST),
            ends_at=datetime(2026, 9, 10, 14, 30, tzinfo=KST),
        ),
    ]

    _cascade_item_times(
        db,  # type: ignore[arg-type]
        route,  # type: ignore[arg-type]
        datetime(2026, 9, 10, 10, tzinfo=KST),
        (33.40, 126.20),
        items,
    )

    assert [(item.starts_at, item.ends_at) for item in items] == [(None, None), (None, None)]


def test_fit_edited_visit_waits_until_break_ends() -> None:
    business_hours = SimpleNamespace(
        is_closed=False,
        opens_at=time(9),
        closes_at=time(19),
        break_start_at=time(12),
        break_end_at=time(13),
    )
    item = SimpleNamespace(place_id=uuid.uuid4(), stay_minutes=60)
    route = SimpleNamespace(
        pace=TripPace.NORMAL,
        end_at=datetime(2026, 9, 10, 22, tzinfo=KST),
    )

    visit = _fit_edited_item_visit(
        FakeSession(scalar_result=business_hours),  # type: ignore[arg-type]
        item,  # type: ignore[arg-type]
        datetime(2026, 9, 10, 11, 30, tzinfo=KST),
        route,  # type: ignore[arg-type]
    )

    assert visit == (
        datetime(2026, 9, 10, 13, tzinfo=KST),
        datetime(2026, 9, 10, 14, tzinfo=KST),
    )
