import pytest

from app.recommend.config.weights import (
    INITIAL_WEIGHTS,
    PRESET_MULTIPLIERS,
    USER_CRITERIA_BOOST,
)
from app.recommend.weights import resolve_weights


def test_initial_weights_sum_to_one() -> None:
    assert INITIAL_WEIGHTS == {
        "preference": 0.30,
        "pet": 0.32,
        "proximity": 0.23,
        "rating": 0.0,
        "weather": 0.15,
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
