import uuid

import pytest

from app.db.models.enums import PetPolicyType, PlaceEnvironment
from app.recommend.config.weights import (
    INITIAL_WEIGHTS,
    PRESET_MULTIPLIERS,
    USER_CRITERIA_BOOST,
)
from app.recommend.schemas import Candidate, PetPolicy, Weights
from app.recommend.scoring import ScoringContext, score_candidates
from app.recommend.weights import backfill_weather_signal, resolve_weights


def test_initial_weights_sum_to_one() -> None:
    assert INITIAL_WEIGHTS == {
        "preference": 0.22,
        "pet": 0.50,
        "proximity": 0.28,
        "rating": 0.0,
        "weather": 0.0,
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
        "healing": {},
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
        ["preference", "pet", "proximity"],
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


def test_healing_preset_and_weather_criterion_leave_weather_signal() -> None:
    """[Phase 5] weather 축은 0 이지만 healing·weather 기준은 스냅샷에 고정 신호를 남긴다.

    생성기는 weights.weather > 0 을 실내 우선 규칙(indoor_bias)의 신호로 읽는다.
    balanced 는 0(신호 없음), healing·weather 기준은 0.10 을 정규화한 양수.
    """
    balanced = resolve_weights("balanced")
    assert balanced.weather == 0.0

    healing = resolve_weights("healing")
    assert healing != balanced
    assert healing.weather > 0
    # weather 0.10 을 얹고 정규화(pet .50/prox .28/pref .22 = 1.0, +0.10 → /1.10).
    assert healing.weather == pytest.approx(0.10 / 1.10)

    weather_boost = resolve_weights(user_criteria=["weather"])
    assert weather_boost.weather == pytest.approx(0.10 / 1.10)


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


def test_backfill_zeroes_weather_for_non_healing_snapshot() -> None:
    # 옛 balanced 스냅샷(weather 0.15 등 양수) → weather 0, 합 1 유지.
    old = {
        "preference": 0.20,
        "pet": 0.45,
        "proximity": 0.25,
        "rating": 0.0,
        "weather": 0.10,
        "popularity": 0.0,
    }

    result = backfill_weather_signal(old, "balanced")

    assert result["weather"] == 0.0
    assert sum(result.values()) == pytest.approx(1.0)
    # Weights 검증기(합 1·6키)를 통과해야 편집 API 가 500 이 안 난다.
    assert Weights(**result)


def test_backfill_keeps_weather_signal_for_healing_snapshot() -> None:
    old = {
        "preference": 0.18,
        "pet": 0.41,
        "proximity": 0.23,
        "rating": 0.0,
        "weather": 0.18,
        "popularity": 0.0,
    }

    result = backfill_weather_signal(old, "healing")

    assert result["weather"] > 0
    assert sum(result.values()) == pytest.approx(1.0)
    assert Weights(**result)
    # 다른 축의 상대 비율은 보존된다(weather 만 신호로 교체 후 재정규화).
    assert result["pet"] / result["preference"] == pytest.approx(0.41 / 0.18)
