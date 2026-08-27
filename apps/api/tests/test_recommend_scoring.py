import uuid

import pytest

from app.db.models.enums import PetPolicyType, PlaceEnvironment
from app.recommend.schemas import Candidate, PetPolicy, Weights
from app.recommend.scoring import (
    ScoringContext,
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
        "tags": ["바다", "산책"],
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
        ({"바다", "산책"}, {"바다", "산책"}, 1.0),
        ({"바다"}, {"카페"}, 0.0),
        ({"바다", "산책"}, {"바다", "카페"}, 1 / 3),
        ({"표준외"}, {"표준외"}, 0.0),
    ],
)
def test_preference_uses_standard_tag_jaccard(
    user_tags: set[str], place_tags: set[str], expected: float
) -> None:
    assert preference_score(user_tags, place_tags) == pytest.approx(expected)


def test_weather_has_no_sunny_day_indoor_bias() -> None:
    assert weather_score(PlaceEnvironment.INDOOR, 0) == weather_score(
        PlaceEnvironment.OUTDOOR, 0
    )
    assert weather_score(PlaceEnvironment.INDOOR, 100) > weather_score(
        PlaceEnvironment.OUTDOOR, 100
    )


def test_unknown_environment_gets_neutral_weather_score() -> None:
    assert weather_score(None, 0) == 0.5
    assert weather_score(None, 100) == 0.5


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
    high = _candidate(tags=["바다"], rating_avg=5.0, saved_count=10)
    low = _candidate(tags=["카페"], rating_avg=1.0, saved_count=0)
    context = ScoringContext(
        weights=resolve_weights(),
        base_coord=(33.4996, 126.5312),
        preferred_tags=frozenset({"바다"}),
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
    assert "평점" not in high_result.reason
    assert "인기" not in high_result.reason
