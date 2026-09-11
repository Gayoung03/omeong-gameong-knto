"""이동시간·거리 추정 — 실측(TMAP)으로 보정한 직선거리 기반 추정.

TMAP 캐시가 없거나 호출 상한을 넘겼을 때, 또는 상세 응답에서 캐시가 비었을 때
실제 경로 대신 쓴다.

기존 `haversine/500` 은 짧은 구간의 고정 비용(승·하차, 시내 진출입)을 놓쳐
실측 38구간(TMAP 12 + 캐시 26)에서 평균 33.7% 빗나갔다 — 3km 를 8분으로 봤지만
실제는 17분이었다. 아래 식은 같은 데이터에서 17.1% 로 줄었다.

- 차량: 고정 7분 + 직선거리/600(≈36km/h 실효). 거리는 직선×1.35(해안 1.11~1.17,
  횡단 최대 1.73 사이의 절충).
- 도보: 직선×1.3 / 75(≈4.5km/h). 거리는 직선×1.3.

한라산 횡단 배율(정상 반경 10km ×1.15)을 붙였다가 실측에서 뺐다: 전체 MAPE 가
17.1%→19.0%, 장거리는 15.3%→21.3% 로 오히려 커졌다. 600m/min 이라는 보수적
속도가 산길 우회를 이미 흡수해, 횡단 6구간도 배율 없이 추정/실제 0.89~1.17
(평균 ≈1.03)이었다. 표본이 작아 "산이 무관"이 아니라 "이 식에서는 별도 배율이
불필요"로 기록한다.
"""

import math

from app.db.models.enums import TransportType
from app.recommend.common.geo import haversine_m
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

    return RouteLeg(
        distance_m=round(straight_m * CAR_DISTANCE_FACTOR),
        duration_min=math.ceil(CAR_FIXED_MINUTES + straight_m / CAR_METERS_PER_MINUTE),
        polyline=None,
        source="estimate",
    )
