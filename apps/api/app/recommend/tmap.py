"""TMAP 이동 경로 조회와 DB 캐시."""

import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import RouteCalculationCache
from app.db.models.enums import TransportType

TMAP_BASE_URL = "https://apis.openapi.sk.com/tmap"
CACHE_TTL = timedelta(hours=24)
REQUEST_TIMEOUT_SECONDS = 10.0
CAR_TRANSPORTS = {
    TransportType.RENTAL_CAR,
    TransportType.OWN_CAR,
    TransportType.TAXI,
}


class TMapError(RuntimeError):
    """TMAP 경로를 조회하거나 해석하지 못했다."""


@dataclass(frozen=True)
class RouteLeg:
    distance_m: int
    duration_min: int
    polyline: str | None


def get_route(
    db: Session,
    from_coord: tuple[float, float],
    to_coord: tuple[float, float],
    transport: TransportType,
    depart_at: datetime | None = None,
    *,
    client: httpx.Client | None = None,
    now: datetime | None = None,
) -> RouteLeg:
    """유효한 DB 캐시를 우선 사용하고 없으면 TMAP을 호출한다.

    내부 좌표는 항상 ``(위도, 경도)``다. TMAP 요청을 만들 때만 X/Y 순서로
    뒤집는다. 새 캐시는 호출자의 트랜잭션에 참여하며 여기서는 commit하지 않는다.
    """
    _validate_coord(from_coord)
    _validate_coord(to_coord)
    calculated_at = now or datetime.now(UTC)
    cached = _find_cache(db, from_coord, to_coord, transport, depart_at, calculated_at)
    if cached is not None:
        return _leg_from_cache(cached)

    leg = _request_route(from_coord, to_coord, transport, client=client)
    db.add(
        RouteCalculationCache(
            origin_latitude=_coordinate_decimal(from_coord[0]),
            origin_longitude=_coordinate_decimal(from_coord[1]),
            destination_latitude=_coordinate_decimal(to_coord[0]),
            destination_longitude=_coordinate_decimal(to_coord[1]),
            transport=transport,
            requested_departure_at=depart_at,
            distance_meters=leg.distance_m,
            duration_minutes=leg.duration_min,
            polyline=leg.polyline,
            calculated_at=calculated_at,
            expires_at=calculated_at + CACHE_TTL,
        )
    )
    db.flush()
    return leg


def _find_cache(
    db: Session,
    from_coord: tuple[float, float],
    to_coord: tuple[float, float],
    transport: TransportType,
    depart_at: datetime | None,
    now: datetime,
) -> RouteCalculationCache | None:
    departure_condition = (
        RouteCalculationCache.requested_departure_at.is_(None)
        if depart_at is None
        else RouteCalculationCache.requested_departure_at == depart_at
    )
    return db.scalar(
        select(RouteCalculationCache)
        .where(
            RouteCalculationCache.origin_latitude == _coordinate_decimal(from_coord[0]),
            RouteCalculationCache.origin_longitude == _coordinate_decimal(from_coord[1]),
            RouteCalculationCache.destination_latitude == _coordinate_decimal(to_coord[0]),
            RouteCalculationCache.destination_longitude == _coordinate_decimal(to_coord[1]),
            RouteCalculationCache.transport == transport,
            departure_condition,
            RouteCalculationCache.expires_at > now,
        )
        .order_by(RouteCalculationCache.calculated_at.desc())
        .limit(1)
    )


def _request_route(
    from_coord: tuple[float, float],
    to_coord: tuple[float, float],
    transport: TransportType,
    *,
    client: httpx.Client | None = None,
) -> RouteLeg:
    if not settings.tmap_api:
        raise TMapError("TMAP_API가 설정되지 않았습니다")

    endpoint = _endpoint_for(transport)
    start_lat, start_lng = from_coord
    end_lat, end_lng = to_coord
    payload = {
        "startX": str(start_lng),
        "startY": str(start_lat),
        "endX": str(end_lng),
        "endY": str(end_lat),
        "startName": "출발지",
        "endName": "도착지",
        "reqCoordType": "WGS84GEO",
        "resCoordType": "WGS84GEO",
    }
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "appKey": settings.tmap_api,
    }

    try:
        if client is None:
            with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as owned_client:
                response = owned_client.post(endpoint, headers=headers, json=payload)
        else:
            response = client.post(endpoint, headers=headers, json=payload)
        response.raise_for_status()
        body = response.json()
    except (httpx.HTTPError, ValueError) as error:
        raise TMapError("TMAP 경로 조회에 실패했습니다") from error

    return _parse_route(body)


def _endpoint_for(transport: TransportType) -> str:
    if transport in CAR_TRANSPORTS:
        path = "routes"
    elif transport is TransportType.WALK:
        path = "routes/pedestrian"
    else:
        raise TMapError(f"지원하지 않는 TMAP 이동수단입니다: {transport.value}")
    return f"{TMAP_BASE_URL}/{path}?version=1&format=json"


def _parse_route(body: object) -> RouteLeg:
    if not isinstance(body, dict) or not isinstance(body.get("features"), list):
        raise TMapError("TMAP 응답에 경로 정보가 없습니다")

    features = body["features"]
    summary: dict[str, object] | None = None
    line_coordinates: list[object] = []
    for feature in features:
        if not isinstance(feature, dict):
            continue
        properties = feature.get("properties")
        if isinstance(properties, dict) and {
            "totalDistance",
            "totalTime",
        }.issubset(properties):
            summary = properties
        geometry = feature.get("geometry")
        if isinstance(geometry, dict) and geometry.get("type") == "LineString":
            coordinates = geometry.get("coordinates")
            if isinstance(coordinates, list):
                line_coordinates.extend(coordinates)

    if summary is None:
        raise TMapError("TMAP 응답에 거리·시간 정보가 없습니다")
    try:
        distance_m = int(summary["totalDistance"])
        duration_seconds = int(summary["totalTime"])
    except (TypeError, ValueError) as error:
        raise TMapError("TMAP 거리·시간 형식이 올바르지 않습니다") from error
    if distance_m < 0 or duration_seconds < 0:
        raise TMapError("TMAP 거리·시간은 음수일 수 없습니다")

    return RouteLeg(
        distance_m=distance_m,
        duration_min=math.ceil(duration_seconds / 60),
        polyline=json.dumps(line_coordinates, ensure_ascii=False) if line_coordinates else None,
    )


def _validate_coord(coord: tuple[float, float]) -> None:
    lat, lng = coord
    if not -90 <= lat <= 90:
        raise ValueError("위도는 -90~90 범위여야 합니다")
    if not -180 <= lng <= 180:
        raise ValueError("경도는 -180~180 범위여야 합니다")


def _coordinate_decimal(value: float) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.0000001"))


def _leg_from_cache(cache: RouteCalculationCache) -> RouteLeg:
    return RouteLeg(
        distance_m=cache.distance_meters,
        duration_min=cache.duration_minutes,
        polyline=cache.polyline,
    )
