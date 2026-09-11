"""실측 기반 이동시간 추정(travel_estimate) 검증.

캘리브레이션 12구간은 TMAP 실측(tmap_calibration.json)을 픽스처로 복사한 것이다.
"""

import math

import pytest

from app.db.models.enums import TransportType
from app.recommend.common.geo import haversine_m
from app.recommend.travel_estimate import estimate_leg

# 실측 좌표 (위도, 경도).
COORDS: dict[str, tuple[float, float]] = {
    "제주공항": (33.5070, 126.4930),
    "성산일출봉": (33.4587, 126.9425),
    "중문": (33.2500, 126.4110),
    "서귀포": (33.2450, 126.5650),
    "애월": (33.4640, 126.3100),
    "협재": (33.3940, 126.2400),
    "함덕": (33.5432, 126.6695),
    "표선": (33.3260, 126.8380),
    "김녕": (33.5580, 126.7590),
    "1100고지": (33.3580, 126.4620),
    "사려니": (33.3900, 126.6730),
    "새별오름": (33.3620, 126.3560),
}

# (from, to, tmap_min) — TMAP 실측 소요시간(분).
CALIBRATION: list[tuple[str, str, int]] = [
    ("제주공항", "서귀포", 65),
    ("제주공항", "중문", 44),
    ("함덕", "서귀포", 69),
    ("함덕", "중문", 73),
    ("애월", "성산일출봉", 77),
    ("협재", "표선", 87),
    ("김녕", "성산일출봉", 38),
    ("제주공항", "성산일출봉", 65),
    ("새별오름", "사려니", 54),
    ("중문", "성산일출봉", 84),
    ("서귀포", "1100고지", 37),
    ("함덕", "표선", 45),
]

@pytest.mark.parametrize(("frm", "to", "tmap_min"), CALIBRATION)
def test_car_estimate_ratio_within_bounds(frm: str, to: str, tmap_min: int) -> None:
    # 배율 없는 7+직선/600 은 전 구간 0.75~1.40(현재 최대 1.36, 애월→성산).
    leg = estimate_leg(COORDS[frm], COORDS[to], TransportType.RENTAL_CAR)
    ratio = leg.duration_min / tmap_min
    assert 0.75 <= ratio <= 1.40, f"{frm}->{to} ratio={ratio:.2f}"
    assert leg.source == "estimate"


def test_walk_uses_walk_factor_and_speed() -> None:
    a, b = (33.5000, 126.5300), (33.5050, 126.5300)
    leg = estimate_leg(a, b, TransportType.WALK)
    straight = haversine_m(a, b)
    assert leg.distance_m == round(straight * 1.3)
    assert leg.duration_min == math.ceil(straight * 1.3 / 75)
    assert leg.source == "estimate"
    # 같은 구간이라도 도보가 차량보다 오래 걸린다.
    car = estimate_leg(a, b, TransportType.RENTAL_CAR)
    assert leg.duration_min > car.duration_min


def test_duration_is_monotonic_in_distance() -> None:
    # 한라산에서 먼 북쪽 해안 위에서 거리만 늘린다(횡단 배율 개입 없음).
    base = (33.5500, 126.3000)
    points = [(33.5500, 126.4000), (33.5500, 126.6000), (33.5500, 126.8000)]
    durations = [
        estimate_leg(base, point, TransportType.RENTAL_CAR).duration_min for point in points
    ]
    assert durations == sorted(durations)
    assert durations[0] < durations[-1]


def test_unsupported_transport_raises() -> None:
    with pytest.raises(ValueError, match="지원하지 않는"):
        estimate_leg((33.5, 126.5), (33.4, 126.5), TransportType.FERRY)
