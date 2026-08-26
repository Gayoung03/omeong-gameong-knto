"""외부 지도 API 호출 전 후보 축소에 쓰는 직선거리 계산."""

from math import asin, cos, radians, sin, sqrt

EARTH_RADIUS_M = 6_371_008.8


def haversine_m(from_coord: tuple[float, float], to_coord: tuple[float, float]) -> float:
    """(위도, 경도) 두 좌표의 대권 거리를 미터로 반환한다."""

    lat1, lng1 = from_coord
    lat2, lng2 = to_coord
    for lat in (lat1, lat2):
        if not -90 <= lat <= 90:
            raise ValueError("위도는 -90~90 범위여야 합니다")
    for lng in (lng1, lng2):
        if not -180 <= lng <= 180:
            raise ValueError("경도는 -180~180 범위여야 합니다")

    phi1, phi2 = radians(lat1), radians(lat2)
    delta_phi = radians(lat2 - lat1)
    delta_lng = radians(lng2 - lng1)
    hav = sin(delta_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(delta_lng / 2) ** 2
    return 2 * EARTH_RADIUS_M * asin(sqrt(hav))


# 기획 문서의 함수명. 단위가 드러나는 이름도 함께 제공한다.
haversine = haversine_m
