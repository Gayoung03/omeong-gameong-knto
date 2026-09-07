"""외부 지도 API 호출 전 후보 축소에 쓰는 직선거리 계산."""

from math import asin, cos, hypot, radians, sin, sqrt

EARTH_RADIUS_M = 6_371_008.8
Coordinate = tuple[float, float]


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


def distance_to_segment_m(point: Coordinate, a: Coordinate, b: Coordinate) -> float:
    """점에서 선분 a-b 까지의 최소 거리(m).

    제주 규모(~70km)에서는 등장방형(equirectangular) 근사로 충분하다. 선분의
    중간 위도를 기준으로 좌표를 평면(m)에 투영한 뒤 점-선분 거리를 구한다.
    투영점이 선분 양끝 밖으로 나가면 가까운 끝점까지의 거리를 돌려준다.
    """

    ref_lat = radians((a[0] + b[0]) / 2)

    def _xy(coord: Coordinate) -> Coordinate:
        lat, lng = coord
        return radians(lng) * EARTH_RADIUS_M * cos(ref_lat), radians(lat) * EARTH_RADIUS_M

    px, py = _xy(point)
    ax, ay = _xy(a)
    bx, by = _xy(b)
    dx, dy = bx - ax, by - ay
    segment_length_sq = dx * dx + dy * dy
    if segment_length_sq == 0:
        return hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / segment_length_sq
    t = max(0.0, min(1.0, t))
    nearest_x, nearest_y = ax + t * dx, ay + t * dy
    return hypot(px - nearest_x, py - nearest_y)


# 기획 문서의 함수명. 단위가 드러나는 이름도 함께 제공한다.
haversine = haversine_m
