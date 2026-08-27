"""추천 서비스의 좌표·요청 계약 단위 테스트."""

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.integrations.maps.kakao import GeocodedAddress
from app.schemas.route import RouteRequestCreate, RouteRequestStayCreate
from app.services.route_recommendation import resolve_location

KST = timezone(timedelta(hours=9))


class FakeSession:
    def __init__(self, place: object | None = None) -> None:
        self.place = place

    def get(self, _model: object, _place_id: uuid.UUID) -> object | None:
        return self.place


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
