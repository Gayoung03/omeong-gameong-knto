from app.db.models.enums import (
    PetActivityLevel,
    PetEnergyLevel,
    TripPace,
)
from app.recommend.config.pace import (
    CAR_SICKNESS_MAX_TRAVEL_MIN,
    PACE,
    effective_rule,
)
from app.recommend.schemas import PetProfile


def test_all_trip_paces_have_itinerary_rules() -> None:
    assert set(PACE) == {pace.value for pace in TripPace}


def test_relaxed_pace_contract() -> None:
    relaxed = PACE[TripPace.RELAXED]

    assert relaxed["places_per_day"] == 3
    assert relaxed["rest_min"] == 110
    assert relaxed["window"] == ("10:00", "19:00")
    assert relaxed["max_travel_min"] is None


def test_effective_rule_without_pets_matches_base() -> None:
    assert effective_rule(TripPace.NORMAL, []) == PACE[TripPace.NORMAL]


def test_effective_rule_does_not_mutate_base_table() -> None:
    base_before = dict(PACE[TripPace.NORMAL])

    effective_rule(TripPace.NORMAL, [PetProfile(car_sickness=True, age_years=10)])

    assert PACE[TripPace.NORMAL] == base_before


def test_senior_pet_reduces_places_and_adds_rest() -> None:
    base = PACE[TripPace.NORMAL]

    rule = effective_rule(TripPace.NORMAL, [PetProfile(age_years=8)])

    assert rule["places_per_day"] == base["places_per_day"] - 1
    assert rule["rest_min"] == base["rest_min"] + 15


def test_low_activity_or_energy_slows_the_day() -> None:
    for pet in (
        PetProfile(activity_level=PetActivityLevel.LOW),
        PetProfile(energy_level=PetEnergyLevel.LOW),
    ):
        rule = effective_rule(TripPace.NORMAL, [pet])
        assert rule["places_per_day"] == PACE[TripPace.NORMAL]["places_per_day"] - 1
        assert rule["rest_min"] == PACE[TripPace.NORMAL]["rest_min"] + 15


def test_slowdown_floors_places_at_two() -> None:
    # relaxed 는 3장소 → 2장소로 내려가되 그 아래로는 내려가지 않는다.
    rule = effective_rule(TripPace.RELAXED, [PetProfile(age_years=12)])

    assert rule["places_per_day"] == 2


def test_high_energy_active_pet_keeps_base_day() -> None:
    rule = effective_rule(
        TripPace.NORMAL,
        [PetProfile(activity_level=PetActivityLevel.HIGH, energy_level=PetEnergyLevel.HIGH)],
    )

    assert rule["places_per_day"] == PACE[TripPace.NORMAL]["places_per_day"]
    assert rule["rest_min"] == PACE[TripPace.NORMAL]["rest_min"]


def test_trip_energy_overrides_baseline_activity_level() -> None:
    # 계약 §3.4: energy_level > activity_level. 평소 저활동이어도 이번 컨디션이
    # 좋으면(HIGH) 감속하지 않고, 평소 활발해도 이번 컨디션이 나쁘면(LOW) 감속한다.
    base = PACE[TripPace.NORMAL]

    not_slowed = effective_rule(
        TripPace.NORMAL,
        [PetProfile(activity_level=PetActivityLevel.LOW, energy_level=PetEnergyLevel.HIGH)],
    )
    assert not_slowed["places_per_day"] == base["places_per_day"]
    assert not_slowed["rest_min"] == base["rest_min"]

    slowed = effective_rule(
        TripPace.NORMAL,
        [PetProfile(activity_level=PetActivityLevel.HIGH, energy_level=PetEnergyLevel.LOW)],
    )
    assert slowed["places_per_day"] == base["places_per_day"] - 1
    assert slowed["rest_min"] == base["rest_min"] + 15


def test_car_sickness_caps_travel_and_adds_rest() -> None:
    base = PACE[TripPace.NORMAL]

    rule = effective_rule(TripPace.NORMAL, [PetProfile(car_sickness=True)])

    assert rule["max_travel_min"] == CAR_SICKNESS_MAX_TRAVEL_MIN
    assert rule["rest_min"] == base["rest_min"] + 10
    assert rule["places_per_day"] == base["places_per_day"]


def test_slow_and_car_sick_pet_stacks_both_adjustments() -> None:
    base = PACE[TripPace.NORMAL]

    rule = effective_rule(
        TripPace.NORMAL,
        [PetProfile(age_years=10, car_sickness=True)],
    )

    assert rule["places_per_day"] == base["places_per_day"] - 1
    assert rule["rest_min"] == base["rest_min"] + 25
    assert rule["max_travel_min"] == CAR_SICKNESS_MAX_TRAVEL_MIN
