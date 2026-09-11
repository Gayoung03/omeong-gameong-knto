"""동선·숙소 근처 동물병원 안전망 (docs/api/routes.md "nearbyAnimalHospitals 안전망 규칙").

응답 시점 계산값 — 저장하지 않는다. 여행 항목(출발지·숙소 앵커 포함)의 앵커 좌표를
중심으로 `places.category_detail = '동물병원'` 을 bounding-box 로 좁힌 뒤 haversine 로
최소 거리를 재고, 이름의 "24시" 판정으로 24시 우선 → 거리순 정렬한다.
"""

import uuid
from dataclasses import dataclass
from math import cos, radians

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Place
from app.recommend.common.geo import haversine_m

HOSPITAL_CATEGORY_DETAIL = "동물병원"
#: 앵커에서 이 반경(m) 안의 병원만 안전망에 넣는다.
HOSPITAL_SEARCH_RADIUS_M = 5000.0
#: 응답에 담는 최대 병원 수.
MAX_HOSPITALS = 3
#: 영업시간 데이터가 없어 이름의 이 표기로만 24시 여부를 판정한다.
H24_MARKER = "24시"
#: 위도 1도의 대략 거리(m). bounding-box 폭 계산용.
_LAT_DEGREE_M = 111_000.0

Coordinate = tuple[float, float]


@dataclass(frozen=True)
class HospitalCandidate:
    """bounding-box 로 좁힌 병원 원본(거리 계산 전)."""

    id: uuid.UUID
    name: str
    address: str | None
    phone: str | None
    latitude: float
    longitude: float


@dataclass(frozen=True)
class NearbyHospital:
    """앵커까지 최소 거리와 24시 판정을 매긴 결과."""

    id: uuid.UUID
    name: str
    address: str | None
    phone: str | None
    latitude: float
    longitude: float
    distance_meters: int
    is_24h: bool


def is_24h(name: str) -> bool:
    return H24_MARKER in name


def _bounding_box(anchors: list[Coordinate], radius_m: float) -> tuple[float, float, float, float]:
    """앵커 전체를 감싸고 반경만큼 넓힌 (min_lat, max_lat, min_lng, max_lng)."""
    lats = [lat for lat, _ in anchors]
    lngs = [lng for _, lng in anchors]
    delta_lat = radius_m / _LAT_DEGREE_M
    # 경도 1도의 거리는 cos(위도)배로 좁아진다. 가장 넓어지는(코사인 최소) 위도로
    # 보수적으로 잡아 후보를 놓치지 않는다.
    min_cos = max(min(cos(radians(lat)) for lat in lats), 1e-6)
    delta_lng = radius_m / (_LAT_DEGREE_M * min_cos)
    return (
        min(lats) - delta_lat,
        max(lats) + delta_lat,
        min(lngs) - delta_lng,
        max(lngs) + delta_lng,
    )


def rank_hospitals(
    anchors: list[Coordinate],
    candidates: list[HospitalCandidate],
    *,
    radius_m: float = HOSPITAL_SEARCH_RADIUS_M,
    limit: int = MAX_HOSPITALS,
) -> list[NearbyHospital]:
    """앵커까지 최소 거리 <= 반경인 병원을 24시 우선 → 거리순으로 최대 limit개."""
    picked: list[NearbyHospital] = []
    for candidate in candidates:
        distance = min(
            haversine_m(anchor, (candidate.latitude, candidate.longitude)) for anchor in anchors
        )
        if distance > radius_m:
            continue
        picked.append(
            NearbyHospital(
                id=candidate.id,
                name=candidate.name,
                address=candidate.address,
                phone=candidate.phone,
                latitude=candidate.latitude,
                longitude=candidate.longitude,
                distance_meters=round(distance),
                is_24h=is_24h(candidate.name),
            )
        )
    picked.sort(key=lambda hospital: (not hospital.is_24h, hospital.distance_meters))
    return picked[:limit]


def nearby_animal_hospitals(db: Session, anchors: list[Coordinate]) -> list[NearbyHospital]:
    """앵커 좌표 기준 근처 동물병원 안전망. 앵커가 없으면 빈 목록."""
    if not anchors:
        return []
    min_lat, max_lat, min_lng, max_lng = _bounding_box(anchors, HOSPITAL_SEARCH_RADIUS_M)
    rows = db.execute(
        select(
            Place.id, Place.name, Place.address, Place.phone, Place.latitude, Place.longitude
        ).where(
            Place.is_active.is_(True),
            Place.category_detail == HOSPITAL_CATEGORY_DETAIL,
            Place.latitude.between(min_lat, max_lat),
            Place.longitude.between(min_lng, max_lng),
        )
    ).all()
    candidates = [
        HospitalCandidate(
            id=row.id,
            name=row.name,
            address=row.address,
            phone=row.phone,
            latitude=float(row.latitude),
            longitude=float(row.longitude),
        )
        for row in rows
    ]
    return rank_hospitals(anchors, candidates)
