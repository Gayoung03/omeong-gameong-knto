import uuid

import pytest

from app.db.models.enums import PetPolicyType, PetSize, PlaceEnvironment, ScheduleItemType
from app.recommend.schemas import Candidate, PetPolicy, PetProfile, Weights
from app.recommend.scoring import (
    ScoringContext,
    _fit_factor,
    pet_score,
    preference_score,
    proximity_score,
    score_candidates,
    weather_score,
)
from app.recommend.weights import resolve_weights


def _candidate(**overrides: object) -> Candidate:
    values = {
        "place_id": uuid.uuid4(),
        "lat": 33.4996,
        "lng": 126.5312,
        "item_type": "attraction",
        "environment": PlaceEnvironment.OUTDOOR,
        "average_stay_minutes": 60,
        "tags": ["sea", "walk"],
        "amenities": [],
        "rating_avg": 4.0,
        "saved_count": 10,
        "pet_policy": PetPolicy(
            policy_type=PetPolicyType.INDOOR_ALLOWED,
            reliability_score=100,
        ),
        "business_hours": [],
    }
    values.update(overrides)
    return Candidate(**values)


@pytest.mark.parametrize(
    ("user_tags", "place_tags", "expected"),
    [
        ({"sea", "walk"}, {"sea", "walk"}, 1.0),
        ({"sea"}, {"cafe"}, 0.0),
        ({"sea", "walk"}, {"sea", "cafe"}, 1 / 3),
        ({"표준외"}, {"표준외"}, 0.0),
    ],
)
def test_preference_uses_standard_tag_jaccard(
    user_tags: set[str], place_tags: set[str], expected: float
) -> None:
    assert preference_score(user_tags, place_tags) == pytest.approx(expected)


def test_preference_can_match_mobile_category_choice() -> None:
    assert preference_score(
        {"category:restaurant"}, set(), ScheduleItemType.RESTAURANT
    ) == pytest.approx(1.0)


def test_weather_has_no_sunny_day_indoor_bias() -> None:
    assert weather_score(PlaceEnvironment.INDOOR, 0) == weather_score(PlaceEnvironment.OUTDOOR, 0)
    assert weather_score(PlaceEnvironment.INDOOR, 100) > weather_score(
        PlaceEnvironment.OUTDOOR, 100
    )


def test_unknown_environment_gets_neutral_weather_score() -> None:
    assert weather_score(None, 0) == 0.5
    assert weather_score(None, 100) == 0.5


def test_missing_forecast_gets_neutral_weather_score() -> None:
    assert weather_score(PlaceEnvironment.INDOOR, None) == 0.5
    assert weather_score(PlaceEnvironment.OUTDOOR, None) == 0.5


def test_proximity_is_one_at_base_and_zero_beyond_limit() -> None:
    base = (33.4996, 126.5312)

    assert proximity_score(base, base, 1_000) == 1
    assert proximity_score(base, (33.0, 126.0), 1_000) == 0


def test_unknown_pet_policy_is_halved() -> None:
    known = _candidate(
        pet_policy=PetPolicy(policy_type=PetPolicyType.INDOOR_ALLOWED, reliability_score=100)
    )
    unknown = _candidate(
        pet_policy=PetPolicy(policy_type=PetPolicyType.UNKNOWN, reliability_score=100)
    )

    assert pet_score(unknown) < pet_score(known)
    assert pet_score(unknown) == pytest.approx(0.25)


def test_score_candidates_returns_contract_sorted_by_total_score() -> None:
    high = _candidate(tags=["sea"], rating_avg=5.0, saved_count=10)
    low = _candidate(tags=["cafe"], rating_avg=1.0, saved_count=0)
    context = ScoringContext(
        weights=resolve_weights(),
        base_coord=(33.4996, 126.5312),
        preferred_tags=frozenset({"sea"}),
    )

    result = score_candidates([low, high], context)

    assert [item.place_id for item in result] == [high.place_id, low.place_id]
    assert set(result[0].sub_scores) == set(Weights.model_fields)
    assert result[0].reason
    assert 0 <= result[0].total_score <= 1


def test_popularity_handles_candidate_set_with_no_saves() -> None:
    candidate = _candidate(saved_count=0)
    context = ScoringContext(weights=resolve_weights(), base_coord=(candidate.lat, candidate.lng))

    result = score_candidates([candidate], context)

    assert result[0].sub_scores["popularity"] == 0


def test_rating_and_popularity_do_not_change_balanced_total_score() -> None:
    place_id = uuid.uuid4()
    low_signals = _candidate(place_id=place_id, rating_avg=1.0, saved_count=0)
    high_signals = _candidate(place_id=place_id, rating_avg=5.0, saved_count=10_000)
    context = ScoringContext(
        weights=resolve_weights("balanced"),
        base_coord=(low_signals.lat, low_signals.lng),
        preferred_tags=frozenset(low_signals.tags),
    )

    low_result = score_candidates([low_signals], context)[0]
    high_result = score_candidates([high_signals], context)[0]

    assert low_result.sub_scores["rating"] != high_result.sub_scores["rating"]
    assert low_result.sub_scores["popularity"] != high_result.sub_scores["popularity"]
    assert low_result.total_score == pytest.approx(high_result.total_score)
    # 근거 문장은 점수 나열이 아니라 동반 조건 문장이다(의미 변경 Phase 6).
    assert high_result.reason.startswith("실내외 동반 가능")
    assert "점" not in high_result.reason


def test_fit_factor_weight_over_seventy_percent_penalized() -> None:
    policy = PetPolicy(policy_type=PetPolicyType.INDOOR_ALLOWED, max_weight_kg=10)
    assert _fit_factor(policy, PetProfile(size=PetSize.SMALL, weight_kg=8)) == pytest.approx(0.85)
    assert _fit_factor(policy, PetProfile(size=PetSize.SMALL, weight_kg=7)) == pytest.approx(1.0)


def test_fit_factor_carrier_by_size() -> None:
    policy = PetPolicy(policy_type=PetPolicyType.INDOOR_ALLOWED, carrier_required=True)
    assert _fit_factor(policy, PetProfile(size=PetSize.LARGE)) == pytest.approx(0.6)
    assert _fit_factor(policy, PetProfile(size=PetSize.MEDIUM)) == pytest.approx(0.8)
    assert _fit_factor(policy, PetProfile(size=PetSize.SMALL)) == pytest.approx(1.0)


def test_fit_factor_muzzle_only_penalizes_large() -> None:
    policy = PetPolicy(policy_type=PetPolicyType.INDOOR_ALLOWED, muzzle_required=True)
    assert _fit_factor(policy, PetProfile(size=PetSize.LARGE)) == pytest.approx(0.9)
    assert _fit_factor(policy, PetProfile(size=PetSize.SMALL)) == pytest.approx(1.0)


def test_fit_factor_size_exclusion_zeroes() -> None:
    policy = PetPolicy(policy_type=PetPolicyType.INDOOR_ALLOWED, allowed_sizes=["small"])
    assert _fit_factor(policy, PetProfile(size=PetSize.LARGE)) == 0.0


def test_fit_factor_unknown_size_skips_carrier_and_exclusion() -> None:
    # size 미상이면 이동장·허용 크기 조건을 걸 수 없어 감점·제외하지 않는다.
    policy = PetPolicy(
        policy_type=PetPolicyType.INDOOR_ALLOWED,
        carrier_required=True,
        muzzle_required=True,
        allowed_sizes=["small"],
    )
    assert _fit_factor(policy, PetProfile(size=None)) == pytest.approx(1.0)


def test_fit_factor_unknown_weight_skips_overweight_penalty() -> None:
    # 체중 미상이면 최대 허용 체중 대비 초과를 판단할 수 없어 감점하지 않는다.
    policy = PetPolicy(policy_type=PetPolicyType.INDOOR_ALLOWED, max_weight_kg=10)
    assert _fit_factor(policy, PetProfile(size=PetSize.SMALL, weight_kg=None)) == pytest.approx(1.0)


def test_pet_score_applies_min_fit_across_pets() -> None:
    # 정책: INDOOR_ALLOWED·carrier_required·reliability 100 → base 0.85.
    candidate = _candidate(
        pet_policy=PetPolicy(
            policy_type=PetPolicyType.INDOOR_ALLOWED,
            carrier_required=True,
            reliability_score=100,
        )
    )
    small = PetProfile(size=PetSize.SMALL)
    large = PetProfile(size=PetSize.LARGE)

    # 반려동물 없음 → base 그대로.
    assert pet_score(candidate) == pytest.approx(0.85)
    # 소형만 → carrier 계수 1.0.
    assert pet_score(candidate, [small]) == pytest.approx(0.85)
    # 대형 포함 → 가장 덜 맞는(대형 0.6) 기준.
    assert pet_score(candidate, [small, large]) == pytest.approx(0.85 * 0.6)
