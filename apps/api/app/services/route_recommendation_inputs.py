"""추천 생성·편집이 공유하는 입력 로딩 — 좌표 해석·반려동물·숙소·출발지.

`route_recommendation`(생성·편집 orchestrator)와 `route_recommendation_replacements`
가 같은 조회를 쓰도록 여기에 모은다. 이 모듈은 상위 orchestrator 를 import 하지
않는다(단방향).
"""

import uuid
from collections.abc import Callable
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Pet, Place, RouteRequest, RouteRequestPet, RouteRequestStay
from app.db.models.enums import PetEnergyLevel
from app.integrations.maps.kakao import GeocodedAddress, geocode_address
from app.recommend.common.geo import Coordinate
from app.recommend.schemas import PetProfile
from app.schemas.pet import calculate_age
from app.services.route_recommendation_errors import LocationResolutionError

Geocoder = Callable[[str], GeocodedAddress]
LinkedPet = tuple[Pet, PetEnergyLevel | None]


def resolve_location(
    db: Session,
    place_id: uuid.UUID | None,
    address: str | None,
    *,
    geocoder: Geocoder = geocode_address,
) -> Coordinate:
    """DB 장소 좌표를 우선 사용하고, 없을 때만 주소를 변환한다."""

    if place_id is not None:
        place = db.get(Place, place_id)
        if place is None:
            raise LocationResolutionError("DB에서 장소를 찾지 못했습니다")
        return float(place.latitude), float(place.longitude)

    if address and address.strip():
        try:
            result = geocoder(address)
        except Exception as error:
            raise LocationResolutionError(
                "주소 또는 장소명을 좌표로 변환하지 못했습니다"
            ) from error
        return result.latitude, result.longitude

    raise LocationResolutionError("장소 ID 또는 주소가 필요합니다")


def _linked_pets(db: Session, request: RouteRequest) -> list[LinkedPet]:
    """요청에 연결된 반려동물과 이번 여행 컨디션(energy_level)을 한 번에 읽는다.

    필터(반려 정책 판정)는 Pet 을, 점수·하루 구성은 energy_level 을 함께 써서,
    _request_inputs 와 _pet_profiles 가 같은 조회를 두 번 하지 않게 공용화한다.
    """
    rows = db.execute(
        select(Pet, RouteRequestPet.energy_level)
        .join(RouteRequestPet, RouteRequestPet.pet_id == Pet.id)
        .where(RouteRequestPet.route_request_id == request.id)
        .order_by(Pet.id)
    ).all()
    return [(pet, energy_level) for pet, energy_level in rows]


def _pet_profiles_from(linked_pets: list[LinkedPet]) -> tuple[PetProfile, ...]:
    """이미 조회한 반려동물+컨디션으로 반려 점수·하루 구성용 프로필을 만든다."""
    return tuple(
        PetProfile(
            size=pet.size,
            weight_kg=float(pet.weight_kg) if pet.weight_kg is not None else None,
            age_years=calculate_age(pet.birth_date),
            activity_level=pet.activity_level,
            car_sickness=pet.car_sickness,
            energy_level=energy_level,
        )
        for pet, energy_level in linked_pets
    )


def _request_inputs(
    db: Session,
    request: RouteRequest,
) -> tuple[list[LinkedPet], list[tuple[RouteRequestStay, Coordinate]], Coordinate]:
    linked_pets = _linked_pets(db, request)
    stays = list(
        db.scalars(
            select(RouteRequestStay)
            .where(RouteRequestStay.route_request_id == request.id)
            .order_by(RouteRequestStay.check_in_at.nulls_last(), RouteRequestStay.id)
        ).all()
    )
    stay_coords = [
        (
            stay,
            (
                (float(stay.latitude), float(stay.longitude))
                if stay.latitude is not None and stay.longitude is not None
                else resolve_location(db, stay.place_id, stay.address)
            ),
        )
        for stay in stays
    ]
    for stay, coord in stay_coords:
        stay.latitude = Decimal(str(coord[0]))
        stay.longitude = Decimal(str(coord[1]))
    if (request.departure_latitude is None or request.departure_longitude is None) and (
        request.departure_place_id is not None or request.departure_location
    ):
        departure_coord = resolve_location(
            db, request.departure_place_id, request.departure_location
        )
        request.departure_latitude = Decimal(str(departure_coord[0]))
        request.departure_longitude = Decimal(str(departure_coord[1]))
    return linked_pets, stay_coords, _start_coord(db, request, stay_coords)


def _start_coord(
    db: Session,
    request: RouteRequest,
    stay_coords: list[tuple[RouteRequestStay, Coordinate]],
) -> Coordinate:
    if request.departure_latitude is not None and request.departure_longitude is not None:
        return float(request.departure_latitude), float(request.departure_longitude)
    if request.departure_place_id is not None or request.departure_location:
        return resolve_location(db, request.departure_place_id, request.departure_location)
    if stay_coords:
        return stay_coords[0][1]
    raise LocationResolutionError("출발 장소 또는 숙소 좌표가 필요합니다")
