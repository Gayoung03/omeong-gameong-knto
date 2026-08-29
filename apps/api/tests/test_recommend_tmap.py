"""TMAP 경로 조회·캐시 단위 테스트."""

import json
from datetime import UTC, datetime
from types import SimpleNamespace

import httpx
import pytest

from app.core.config import settings
from app.db.models.enums import TransportType
from app.recommend import tmap
from app.recommend.tmap import RouteLeg, TMapError


class FakeSession:
    def __init__(self, cached: object | None = None) -> None:
        self.cached = cached
        self.added: list[object] = []
        self.flush_count = 0

    def scalar(self, _statement: object) -> object | None:
        return self.cached

    def add(self, value: object) -> None:
        self.added.append(value)

    def flush(self) -> None:
        self.flush_count += 1


def _response() -> dict[str, object]:
    return {
        "features": [
            {
                "properties": {"totalDistance": 5210, "totalTime": 1081},
                "geometry": {"type": "Point", "coordinates": [126.5, 33.5]},
            },
            {
                "properties": {},
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[126.5, 33.5], [126.6, 33.6]],
                },
            },
        ]
    }


@pytest.mark.parametrize(
    "transport,path",
    [
        (TransportType.RENTAL_CAR, "/tmap/routes"),
        (TransportType.OWN_CAR, "/tmap/routes"),
        (TransportType.TAXI, "/tmap/routes"),
        (TransportType.WALK, "/tmap/routes/pedestrian"),
    ],
)
def test_tmap_request_uses_transport_endpoint_and_xy_coordinates(
    transport: TransportType,
    path: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "tmap_api", "test-key")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == path
        assert request.headers["appKey"] == "test-key"
        payload = json.loads(request.content)
        assert payload["startX"] == "126.5312"
        assert payload["startY"] == "33.4996"
        assert payload["endX"] == "126.2396"
        assert payload["endY"] == "33.3939"
        return httpx.Response(200, json=_response())

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        leg = tmap._request_route(
            (33.4996, 126.5312),
            (33.3939, 126.2396),
            transport,
            client=client,
        )

    assert leg == RouteLeg(
        distance_m=5210,
        duration_min=19,
        polyline="[[126.5, 33.5], [126.6, 33.6]]",
    )


def test_unsupported_transport_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "tmap_api", "test-key")

    with pytest.raises(TMapError, match="지원하지 않는"):
        tmap._request_route(
            (33.4996, 126.5312),
            (33.3939, 126.2396),
            TransportType.PUBLIC_TRANSPORT,
        )


def test_missing_api_key_fails_before_request(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "tmap_api", "")

    with pytest.raises(TMapError, match="TMAP_API"):
        tmap._request_route(
            (33.4996, 126.5312),
            (33.3939, 126.2396),
            TransportType.RENTAL_CAR,
        )


def test_get_route_returns_valid_cache_without_calling_tmap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cached = SimpleNamespace(distance_meters=1200, duration_minutes=7, polyline=None)
    db = FakeSession(cached)
    monkeypatch.setattr(
        tmap,
        "_request_route",
        lambda *_args, **_kwargs: pytest.fail("캐시 적중 시 TMAP을 호출하면 안 됩니다"),
    )

    leg = tmap.get_route(
        db,  # type: ignore[arg-type]
        (33.4996, 126.5312),
        (33.3939, 126.2396),
        TransportType.RENTAL_CAR,
    )

    assert leg == RouteLeg(distance_m=1200, duration_min=7, polyline=None)
    assert db.added == []


def test_get_route_caches_tmap_result(monkeypatch: pytest.MonkeyPatch) -> None:
    db = FakeSession()
    expected = RouteLeg(distance_m=5210, duration_min=19, polyline="[]")
    monkeypatch.setattr(tmap, "_request_route", lambda *_args, **_kwargs: expected)
    now = datetime(2026, 8, 27, tzinfo=UTC)

    leg = tmap.get_route(
        db,  # type: ignore[arg-type]
        (33.4996, 126.5312),
        (33.3939, 126.2396),
        TransportType.RENTAL_CAR,
        now=now,
    )

    assert leg == expected
    assert db.flush_count == 1
    assert len(db.added) == 1
    cache = db.added[0]
    assert cache.origin_latitude == tmap._coordinate_decimal(33.4996)
    assert cache.origin_longitude == tmap._coordinate_decimal(126.5312)
    assert cache.distance_meters == 5210
    assert cache.duration_minutes == 19
    assert cache.expires_at - cache.calculated_at == tmap.CACHE_TTL


def test_get_cached_route_returns_latest_leg_without_requesting_tmap() -> None:
    cached = SimpleNamespace(distance_meters=3400, duration_minutes=12, polyline="[]")
    db = FakeSession(cached)

    leg = tmap.get_cached_route(
        db,  # type: ignore[arg-type]
        (33.4996, 126.5312),
        (33.3939, 126.2396),
        TransportType.RENTAL_CAR,
    )

    assert leg == RouteLeg(distance_m=3400, duration_min=12, polyline="[]")


def test_get_cached_route_returns_none_when_cache_is_missing() -> None:
    leg = tmap.get_cached_route(
        FakeSession(),  # type: ignore[arg-type]
        (33.4996, 126.5312),
        (33.3939, 126.2396),
        TransportType.WALK,
    )

    assert leg is None


def test_invalid_tmap_response_is_rejected() -> None:
    with pytest.raises(TMapError, match="거리·시간"):
        tmap._parse_route({"features": []})
