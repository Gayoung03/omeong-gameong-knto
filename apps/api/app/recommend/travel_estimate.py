"""이동시간·거리 추정 — 실측(TMAP)으로 보정한 직선거리 기반 추정.

TMAP 캐시가 없거나 호출 상한을 넘겼을 때, 또는 상세 응답에서 캐시가 비었을 때
실제 경로 대신 쓴다.

기존 `haversine/500` 은 짧은 구간의 고정 비용(승·하차, 시내 진출입)을 놓쳐
실측 38구간(TMAP 12 + 캐시 26)에서 평균 33.7% 빗나갔다 — 3km 를 8분으로 봤지만
실제는 17분이었다. 아래 식은 같은 데이터에서 17.1% 로 줄었다.

- 차량: 고정 7분 + 직선거리/600(≈36km/h 실효). 직선 경로가 한라산 정상 반경 10km
  안을 지나면 횡단·산길 도로배율(실측 1.46~1.73)을 반영해 ×1.15. 거리는 직선×1.35
  (해안 1.11~1.17, 횡단 최대 1.73 사이의 절충).
- 도보: 직선×1.3 / 75(≈4.5km/h). 거리는 직선×1.3.
"""

import math

from app.db.models.enums import TransportType
from app.recommend.common.geo import distance_to_segment_m, haversine_m
from app.recommend.tmap import RouteLeg

Coordinate = tuple[float, float]

CAR_TRANSPORTS = frozenset(
    {TransportType.RENTAL_CAR, TransportType.OWN_CAR, TransportType.TAXI}
)
SUPPORTED_TRANSPORTS = CAR_TRANSPORTS | {TransportType.WALK}

# 차량 추정 상수 (근거: 모듈 docstring).
CAR_FIXED_MINUTES = 7
CAR_METERS_PER_MINUTE = 600
CAR_DISTANCE_FACTOR = 1.35

# 도보 추정 상수.
WALK_DISTANCE_FACTOR = 1.3
WALK_METERS_PER_MINUTE = 75

# 한라산 정상. 직선 경로가 이 반경 안을 지나면 횡단(산길) 배율을 적용한다.
HALLASAN_SUMMIT: Coordinate = (33.3617, 126.5292)
HALLASAN_CROSSING_RADIUS_M = 10_000.0
CROSSING_DURATION_FACTOR = 1.15


def estimate_leg(
    from_coord: Coordinate, to_coord: Coordinate, transport: TransportType
) -> RouteLeg:
    """실측 회귀 기반의 직선거리 이동 추정. source="estimate" 인 RouteLeg."""

    if transport not in SUPPORTED_TRANSPORTS:
        raise ValueError(f"추정을 지원하지 않는 이동수단입니다: {transport.value}")

    straight_m = haversine_m(from_coord, to_coord)

    if transport == TransportType.WALK:
        road_m = straight_m * WALK_DISTANCE_FACTOR
        return RouteLeg(
            distance_m=round(road_m),
            duration_min=math.ceil(road_m / WALK_METERS_PER_MINUTE),
            polyline=None,
            source="estimate",
        )

    minutes = CAR_FIXED_MINUTES + straight_m / CAR_METERS_PER_MINUTE
    if crosses_hallasan(from_coord, to_coord):
        minutes *= CROSSING_DURATION_FACTOR
    return RouteLeg(
        distance_m=round(straight_m * CAR_DISTANCE_FACTOR),
        duration_min=math.ceil(minutes),
        polyline=None,
        source="estimate",
    )


def crosses_hallasan(from_coord: Coordinate, to_coord: Coordinate) -> bool:
    """직선 경로가 한라산 정상 반경 안을 지나는지(횡단·산길 배율 판정)."""

    return (
        distance_to_segment_m(HALLASAN_SUMMIT, from_coord, to_coord)
        <= HALLASAN_CROSSING_RADIUS_M
    )
