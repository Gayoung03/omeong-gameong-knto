from app.recommend.config.stay import (
    DEFAULT_STAY_MINUTES,
    default_stay_minutes,
)


def test_category_defaults_match_policy() -> None:
    assert default_stay_minutes("oreum") == 90
    assert default_stay_minutes("rental_experience") == 90
    assert default_stay_minutes("cafe") == 50
    assert default_stay_minutes("beach") == 60
    assert default_stay_minutes("walking_trail") == 60
    assert default_stay_minutes("attraction") == 60
    assert default_stay_minutes("restaurant") == 60
    assert default_stay_minutes("restaurant_cafe") == 60


def test_unknown_and_none_category_fall_back_to_default() -> None:
    assert default_stay_minutes("pet_service") == DEFAULT_STAY_MINUTES
    assert default_stay_minutes(None) == DEFAULT_STAY_MINUTES
    assert DEFAULT_STAY_MINUTES == 60
