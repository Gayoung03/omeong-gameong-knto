import uuid

import pytest

from app.db.models.enums import PetPolicyType, PlaceEnvironment
from app.recommend.config.weights import (
    INITIAL_WEIGHTS,
    PRESET_MULTIPLIERS,
    USER_CRITERIA_BOOST,
)
from app.recommend.schemas import Candidate, PetPolicy
from app.recommend.scoring import ScoringContext, score_candidates
from app.recommend.weights import resolve_weights


def test_initial_weights_sum_to_one() -> None:
    assert INITIAL_WEIGHTS == {
        "preference": 0.20,
        "pet": 0.45,
        "proximity": 0.25,
        "rating": 0.0,
        "weather": 0.10,
        "popularity": 0.0,
    }
    assert sum(INITIAL_WEIGHTS.values()) == pytest.approx(1.0)
    assert set(INITIAL_WEIGHTS) == {
        "preference",
        "pet",
        "proximity",
        "rating",
        "weather",
        "popularity",
    }


def test_preset_multipliers_match_confirmed_policy() -> None:
    assert PRESET_MULTIPLIERS == {
        "balanced": {},
        "taste": {"preference": 2.0},
        "pet": {"pet": 2.0},
        "proximity": {"proximity": 2.0},
        "healing": {"weather": 2.0},
    }
    assert USER_CRITERIA_BOOST == 2.0


@pytest.mark.parametrize("preset", PRESET_MULTIPLIERS)
def test_every_preset_is_normalized(preset: str) -> None:
    weights = resolve_weights(preset)

    assert sum(weights.model_dump().values()) == pytest.approx(1.0)


def test_missing_and_unknown_preset_fall_back_to_balanced() -> None:
    balanced = resolve_weights("balanced")

    assert resolve_weights() == balanced
    assert resolve_weights("not-yet-supported") == balanced


def test_user_criteria_boosts_selected_weight_without_mutating_constants() -> None:
    before = dict(INITIAL_WEIGHTS)

    boosted = resolve_weights(user_criteria=["pet"])

    assert boosted.pet > resolve_weights().pet
    assert INITIAL_WEIGHTS == before


@pytest.mark.parametrize(
    "criteria",
    [
        ["preference"],
        ["pet", "proximity"],
        ["preference", "pet", "weather"],
    ],
)
def test_manual_criteria_are_equally_doubled_and_normalized(criteria: list[str]) -> None:
    weights = resolve_weights("balanced", criteria).model_dump()
    raw = dict(INITIAL_WEIGHTS)
    for criterion in criteria:
        raw[criterion] *= 2.0
    total = sum(raw.values())

    assert weights == pytest.approx({key: value / total for key, value in raw.items()})
    assert sum(weights.values()) == pytest.approx(1.0)


def test_preset_and_manual_criteria_cannot_be_combined() -> None:
    with pytest.raises(ValueError, match="동시에 적용"):
        resolve_weights("pet", ["proximity"])


def test_unknown_user_criterion_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown"):
        resolve_weights(user_criteria=["unknown"])


def test_healing_preset_and_weather_criterion_stay_effective() -> None:
    """weather=0 이면 healing·weather 기준이 balanced 와 같아져 조용히 무효화된다.

    Phase 5 전까지 weather 를 0 이 아닌 값으로 남겨 앱의 두 선택지를 살려 둔다.
    (기존 test_manual_criteria_are_equally_doubled_and_normalized 는 구현 공식을
    그대로 재현하는 항진명제라 이 무효화를 잡지 못해 별도 케이스로 둔다.)
    """
    balanced = resolve_weights("balanced")

    healing = resolve_weights("healing")
    assert healing != balanced
    assert healing.weather > balanced.weather

    weather_boost = resolve_weights(user_criteria=["weather"])
    assert weather_boost.weather > balanced.weather


def test_taste_preset_does_not_lower_total_than_balanced_for_matching_candidate() -> None:
    """취향 축이 살아난 뒤, taste 프리셋이 같은 후보에서 balanced 보다 총점이 낮아지지 않는다.

    태그 코드 불일치로 preference 가 항상 0이던 시절엔 taste(preference×2)가
    죽은 축에 가중치를 몰아줘 총점이 오히려 낮아졌다. 그 회귀를 막는다.
    """
    candidate = Candidate(
        place_id=uuid.uuid4(),
        lat=33.4996,
        lng=126.5312,
        item_type="attraction",
        environment=PlaceEnvironment.OUTDOOR,
        average_stay_minutes=60,
        tags=["sea", "walk"],
        amenities=[],
        rating_avg=4.0,
        saved_count=10,
        pet_policy=PetPolicy(policy_type=PetPolicyType.INDOOR_ALLOWED, reliability_score=100),
        business_hours=[],
    )
    # 취향은 완전 일치(=1.0)하되 기준점에서 멀어 proximity 를 낮춰, preference 로
    # 가중치가 옮겨갈수록 총점이 오르는 상황을 만든다.
    common = {
        "base_coord": (33.0, 126.0),
        "preferred_tags": frozenset({"sea", "walk"}),
    }
    balanced = score_candidates(
        [candidate], ScoringContext(weights=resolve_weights("balanced"), **common)
    )[0]
    taste = score_candidates(
        [candidate], ScoringContext(weights=resolve_weights("taste"), **common)
    )[0]

    assert taste.total_score >= balanced.total_score
