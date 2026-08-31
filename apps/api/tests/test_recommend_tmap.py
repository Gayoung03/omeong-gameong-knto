"""TMAP 경로 조회·캐시 단위 테스트."""

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import RouteCalculationCache
from app.db.models.enums import TransportType
from app.recommend import tmap
from app.recommend.tmap import RouteLeg, TMapError


class FakeSession:
    def __init__(self, cached: object | None = None) -> None:
        self.cached = cached
        self.added: list[object] = []
        self.flush_count = 0
        self.executed: list[object] = []

    def scalar(self, _statement: object) -> object | None:
        return self.cached

    def add(self, value: object) -> None:
        self.added.append(value)

    def execute(self, statement: object) -> object:
        # 만료 정리 DELETE 를 기록만 한다(순서 검증용). rowcount 만 흉내낸다.
        self.executed.append(statement)
        return SimpleNamespace(rowcount=0)

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
    # 새 캐시 저장 전에 만료 정리 DELETE 를 한 번 실행한다.
    assert len(db.executed) == 1


def test_캐시_키_좌표는_소수4자리로_양자화된다() -> None:
    # 4자리(~11m) 안쪽 미세 차이는 같은 키로 접힌다 → 읽기·쓰기가 같은 행을 가리킨다.
    from decimal import Decimal

    assert tmap._coordinate_decimal(33.49961) == tmap._coordinate_decimal(33.49964)
    assert tmap._coordinate_decimal(33.49961) == Decimal("33.4996")
    # 4자리를 벗어나면(0.001 차이) 다른 키다.
    assert tmap._coordinate_decimal(33.4996) != tmap._coordinate_decimal(33.5006)


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


# --- DB 연동 (TEST_DATABASE_URL 있을 때만) ---------------------------------


def test_근접_좌표는_같은_캐시에_적중한다(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    # 4자리 양자화 덕에 ~11m 안쪽 좌표는 같은 캐시 행에 적중한다(읽기·쓰기 동일 키).
    expected = RouteLeg(distance_m=5210, duration_min=19, polyline="[]")
    monkeypatch.setattr(tmap, "_request_route", lambda *_a, **_k: expected)
    now = datetime(2026, 8, 27, tzinfo=UTC)

    tmap.get_route(
        db, (33.499612, 126.531234), (33.393900, 126.239600),
        TransportType.RENTAL_CAR, now=now,
    )
    # 근접하지만 다른 좌표 — 4자리 반올림은 동일하다.
    monkeypatch.setattr(
        tmap, "_request_route",
        lambda *_a, **_k: pytest.fail("근접 좌표는 기존 캐시에 적중해야 한다"),
    )
    leg = tmap.get_cached_route(
        db, (33.499648, 126.531199), (33.393861, 126.239640),
        TransportType.RENTAL_CAR, now=now,
    )

    assert leg == expected


def test_만료된_캐시행은_새_저장시_정리된다(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = datetime(2026, 8, 27, tzinfo=UTC)
    db.add(
        RouteCalculationCache(
            origin_latitude=Decimal("30.0000"),
            origin_longitude=Decimal("120.0000"),
            destination_latitude=Decimal("31.0000"),
            destination_longitude=Decimal("121.0000"),
            transport=TransportType.WALK,
            distance_meters=100,
            duration_minutes=1,
            calculated_at=now - timedelta(hours=48),
            expires_at=now - timedelta(hours=24),
        )
    )
    db.flush()

    monkeypatch.setattr(tmap, "_request_route", lambda *_a, **_k: RouteLeg(200, 2, None))
    tmap.get_route(
        db, (33.4996, 126.5312), (33.3939, 126.2396), TransportType.WALK, now=now
    )

    expired = db.scalars(
        select(RouteCalculationCache).where(RouteCalculationCache.expires_at <= now)
    ).all()
    assert expired == []
