import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.models import Pet, Place, PlaceBusinessHour, RouteRequest, User
from app.db.models.enums import (
    PetPolicyType,
    PetSize,
    PetSpecies,
    TransportType,
    TripPace,
)
from app.recommend.filters import filter_candidates, is_closed_for_entire_trip, is_pet_compatible
from app.recommend.schemas import BusinessHour, PetPolicy


def _pet(
    *,
    species: PetSpecies = PetSpecies.DOG,
    size: PetSize | None = PetSize.LARGE,
    weight_kg: Decimal | None = Decimal("20"),
) -> Pet:
    return Pet(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        name="멉이",
        species=species,
        size=size,
        weight_kg=weight_kg,
    )


def _policy(**overrides: object) -> PetPolicy:
    values = {
        "policy_type": PetPolicyType.INDOOR_ALLOWED,
        "allowed_species": ["dog"],
        "allowed_sizes": ["small", "medium", "large"],
        "max_weight_kg": 30,
    }
    values.update(overrides)
    return PetPolicy(**values)


def test_unknown_or_missing_pet_policy_passes_hard_filter() -> None:
    pet = _pet()

    assert is_pet_compatible(None, [pet]) is True
    assert is_pet_compatible(_policy(policy_type=PetPolicyType.UNKNOWN), [pet]) is True


def test_not_allowed_policy_is_rejected() -> None:
    assert is_pet_compatible(_policy(policy_type=PetPolicyType.NOT_ALLOWED), [_pet()]) is False


def test_species_size_and_weight_restrictions_are_enforced() -> None:
    pet = _pet()

    assert is_pet_compatible(_policy(allowed_species=["cat"]), [pet]) is False
    assert is_pet_compatible(_policy(allowed_sizes=["small"]), [pet]) is False
    assert is_pet_compatible(_policy(max_weight_kg=10), [pet]) is False


def test_every_companion_must_match_policy() -> None:
    small_dog = _pet(size=PetSize.SMALL, weight_kg=Decimal("5"))
    large_dog = _pet(size=PetSize.LARGE, weight_kg=Decimal("20"))

    assert is_pet_compatible(_policy(allowed_sizes=["small"]), [small_dog, large_dog]) is False


def test_place_is_removed_only_when_every_trip_date_is_closed() -> None:
    # DB 요일: 일=0, 월=1, 화=2
    hours = [
        BusinessHour(day_of_week=1, is_closed=True),
        BusinessHour(day_of_week=2, is_closed=True),
    ]

    assert is_closed_for_entire_trip(hours, [date(2026, 9, 7), date(2026, 9, 8)]) is True
    assert is_closed_for_entire_trip(hours, [date(2026, 9, 7), date(2026, 9, 9)]) is False


def test_business_hours_are_not_used_for_visit_time_filtering() -> None:
    hours = [
        BusinessHour(
            day_of_week=1,
            opens_at=time(10),
            closes_at=time(14),
            is_closed=False,
        )
    ]

    assert is_closed_for_entire_trip(hours, [date(2026, 9, 7)]) is False


def test_filter_candidates_queries_active_places_and_applies_defaults(
    db: Session, owner: User
) -> None:
    start = datetime(2026, 9, 7, 9, tzinfo=timezone(timedelta(hours=9)))
    request = RouteRequest(
        id=uuid.uuid4(),
        user_id=owner.id,
        start_at=start,
        end_at=start + timedelta(days=1),
        pace=TripPace.NORMAL,
        transport=TransportType.RENTAL_CAR,
    )
    active = Place(
        id=uuid.uuid4(),
        name="활성 관광지",
        category="attraction",
        latitude=Decimal("33.4996000"),
        longitude=Decimal("126.5312000"),
        environment=None,
        average_stay_minutes=None,
        is_active=True,
    )
    inactive = Place(
        id=uuid.uuid4(),
        name="비활성 관광지",
        category="attraction",
        latitude=Decimal("33.4000000"),
        longitude=Decimal("126.5000000"),
        is_active=False,
    )
    db.add_all([request, active, inactive])
    db.flush()

    result = filter_candidates(db, request, [])

    matched = next(candidate for candidate in result if candidate.place_id == active.id)
    assert all(candidate.place_id != inactive.id for candidate in result)
    assert matched.environment is None
    assert matched.average_stay_minutes == 60
    assert matched.rating_avg is None
    assert matched.saved_count == 0


def test_filter_candidates_excludes_accommodations_from_visit_candidates(
    db: Session, owner: User
) -> None:
    start = datetime(2026, 9, 7, 9, tzinfo=timezone(timedelta(hours=9)))
    request = RouteRequest(
        id=uuid.uuid4(),
        user_id=owner.id,
        start_at=start,
        end_at=start + timedelta(hours=8),
        pace=TripPace.NORMAL,
        transport=TransportType.RENTAL_CAR,
    )
    accommodation = Place(
        id=uuid.uuid4(),
        name="동선 기준 숙소",
        category="accommodation",
        latitude=Decimal("33.4996000"),
        longitude=Decimal("126.5312000"),
        is_active=True,
    )
    dinner = Place(
        id=uuid.uuid4(),
        name="저녁 식당",
        category="restaurant_cafe",
        latitude=Decimal("33.5000000"),
        longitude=Decimal("126.5300000"),
        is_active=True,
    )
    db.add_all([request, accommodation, dinner])
    db.flush()

    result = filter_candidates(db, request, [])
    stay_results = filter_candidates(db, request, [], include_accommodation=True)

    assert all(candidate.place_id != accommodation.id for candidate in result)
    assert next(
        candidate for candidate in result if candidate.place_id == dinner.id
    ).item_type.value == ("restaurant")
    assert any(candidate.place_id == accommodation.id for candidate in stay_results)


def test_filter_candidates_excludes_place_closed_for_whole_trip(db: Session, owner: User) -> None:
    start = datetime(2026, 9, 7, 9, tzinfo=timezone(timedelta(hours=9)))  # 월요일
    request = RouteRequest(
        id=uuid.uuid4(),
        user_id=owner.id,
        start_at=start,
        end_at=start + timedelta(hours=8),
        pace=TripPace.NORMAL,
        transport=TransportType.RENTAL_CAR,
    )
    closed = Place(
        id=uuid.uuid4(),
        name="월요일 휴무",
        category="cafe",
        latitude=Decimal("33.4996000"),
        longitude=Decimal("126.5312000"),
        is_active=True,
    )
    db.add_all([request, closed])
    db.flush()
    db.add(PlaceBusinessHour(place_id=closed.id, day_of_week=1, is_closed=True))
    db.flush()

    result = filter_candidates(db, request, [])

    assert all(candidate.place_id != closed.id for candidate in result)
