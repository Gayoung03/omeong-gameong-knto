"""1단계 추천 후보 하드 필터와 Candidate 조립."""

import uuid
from collections import defaultdict
from collections.abc import Iterable, Sequence
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    Pet,
    Place,
    PlaceBusinessHour,
    PlacePetPolicy,
    PlaceTag,
    PlaceTagLink,
    RouteRequest,
)
from app.db.models.enums import PetPolicyType, ScheduleItemType
from app.recommend.schemas import BusinessHour, Candidate, PetPolicy
from app.services.place_query import rating_expr, saved_count_expr

DEFAULT_STAY_MINUTES = 60


def is_pet_compatible(policy: PetPolicy | None, pets: Sequence[Pet]) -> bool:
    """정책이 없거나 unknown이면 통과시키고, 명시된 제한만 검사한다."""

    if policy is None or policy.policy_type == PetPolicyType.UNKNOWN:
        return True
    if policy.policy_type == PetPolicyType.NOT_ALLOWED:
        return False

    allowed_species = set(policy.allowed_species)
    allowed_sizes = set(policy.allowed_sizes)
    for pet in pets:
        if allowed_species and pet.species.value not in allowed_species:
            return False
        if pet.size is not None and allowed_sizes and pet.size.value not in allowed_sizes:
            return False
        if (
            pet.weight_kg is not None
            and policy.max_weight_kg is not None
            and float(pet.weight_kg) > policy.max_weight_kg
        ):
            return False
    return True


def is_closed_for_entire_trip(hours: Sequence[BusinessHour], dates: Iterable[date]) -> bool:
    """여행의 모든 날이 명시적 휴무일일 때만 후보에서 제외한다."""

    closed_weekdays = {hour.day_of_week for hour in hours if hour.is_closed}
    travel_dates = set(dates)
    return bool(travel_dates) and all(_db_weekday(day) in closed_weekdays for day in travel_dates)


def filter_candidates(
    db: Session,
    request: RouteRequest,
    pets: Sequence[Pet],
) -> list[Candidate]:
    """활성 장소를 DB에서 축소한 뒤 정책·휴무 조건을 적용한다.

    `route_requests`에 대상 지역 입력이 아직 없으므로 제주 전체를 대상으로
    한다. 지역 계약이 합의되면 이 기본 query에 조건을 추가한다.
    """

    rows = db.execute(
        select(
            Place,
            rating_expr().label("rating_avg"),
            saved_count_expr().label("saved_count"),
        )
        .where(Place.is_active.is_(True))
        .order_by(Place.id)
    ).all()
    if not rows:
        return []

    place_ids = [row.Place.id for row in rows]
    policies = _policies_by_place(db, place_ids)
    hours = _hours_by_place(db, place_ids)
    tags = _tags_by_place(db, place_ids)
    travel_dates = _dates_between(request.start_at.date(), request.end_at.date())

    candidates: list[Candidate] = []
    for row in rows:
        place = row.Place
        item_type = _item_type_of(place.category)
        if item_type is None:
            continue

        policy = policies.get(place.id)
        place_hours = hours.get(place.id, [])
        if not is_pet_compatible(policy, pets):
            continue
        if is_closed_for_entire_trip(place_hours, travel_dates):
            continue

        candidates.append(
            Candidate(
                place_id=place.id,
                lat=float(place.latitude),
                lng=float(place.longitude),
                item_type=item_type,
                environment=place.environment,
                average_stay_minutes=place.average_stay_minutes or DEFAULT_STAY_MINUTES,
                tags=tags.get(place.id, []),
                amenities=place.amenities or [],
                rating_avg=row.rating_avg,
                saved_count=row.saved_count,
                pet_policy=policy,
                business_hours=place_hours,
            )
        )
    return candidates


def _policies_by_place(
    db: Session, place_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, PetPolicy]:
    rows = db.scalars(
        select(PlacePetPolicy)
        .where(PlacePetPolicy.place_id.in_(place_ids))
        .order_by(PlacePetPolicy.place_id, PlacePetPolicy.verified_at.desc().nullslast())
    ).all()
    result: dict[uuid.UUID, PetPolicy] = {}
    for row in rows:
        result.setdefault(
            row.place_id,
            PetPolicy(
                policy_type=row.policy_type,
                allowed_species=row.allowed_species or [],
                allowed_sizes=row.allowed_sizes or [],
                max_weight_kg=(float(row.max_weight_kg) if row.max_weight_kg is not None else None),
                carrier_required=row.carrier_required,
                leash_required=row.leash_required,
                vaccination_required=row.vaccination_required,
                reliability_score=(
                    float(row.reliability_score) if row.reliability_score is not None else None
                ),
            ),
        )
    return result


def _hours_by_place(
    db: Session, place_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, list[BusinessHour]]:
    rows = db.scalars(
        select(PlaceBusinessHour)
        .where(PlaceBusinessHour.place_id.in_(place_ids))
        .order_by(PlaceBusinessHour.place_id, PlaceBusinessHour.day_of_week)
    ).all()
    result: defaultdict[uuid.UUID, list[BusinessHour]] = defaultdict(list)
    for row in rows:
        opens_at, closes_at = row.opens_at, row.closes_at
        if (opens_at is None) != (closes_at is None):
            opens_at = closes_at = None
        result[row.place_id].append(
            BusinessHour(
                day_of_week=row.day_of_week,
                opens_at=opens_at,
                closes_at=closes_at,
                break_start_at=row.break_start_at,
                break_end_at=row.break_end_at,
                is_closed=row.is_closed,
            )
        )
    return dict(result)


def _tags_by_place(
    db: Session, place_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, list[str]]:
    rows = db.execute(
        select(PlaceTagLink.place_id, PlaceTag.code)
        .join(PlaceTag, PlaceTag.id == PlaceTagLink.tag_id)
        .where(PlaceTagLink.place_id.in_(place_ids))
        .order_by(PlaceTagLink.place_id, PlaceTag.code)
    ).all()
    result: defaultdict[uuid.UUID, list[str]] = defaultdict(list)
    for place_id, code in rows:
        result[place_id].append(code)
    return dict(result)


def _dates_between(start: date, end: date) -> list[date]:
    return [start + timedelta(days=offset) for offset in range((end - start).days + 1)]


def _db_weekday(value: date) -> int:
    # Python: 월=0, DB 명세: 일=0.
    return (value.weekday() + 1) % 7


def _item_type_of(category: str) -> ScheduleItemType | None:
    try:
        item_type = ScheduleItemType(category)
    except ValueError:
        return None
    # 숙소는 사용자가 입력한 일자별 동선 기준점이다. 일반 방문 후보로 넘기면
    # 일정 조립기가 숙소를 관광지처럼 배치하므로 추천 후보에서는 제외한다.
    if item_type in {ScheduleItemType.ACCOMMODATION, ScheduleItemType.CUSTOM}:
        return None
    return item_type
