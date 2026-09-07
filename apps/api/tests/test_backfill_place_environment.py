from app.db.models.enums import PetPolicyType, PlaceEnvironment
from scripts.backfill_place_environment import classify


def test_category_rules() -> None:
    assert classify("beach", None, None) == (PlaceEnvironment.OUTDOOR, "category_outdoor")
    assert classify("oreum", None, None) == (PlaceEnvironment.OUTDOOR, "category_outdoor")
    assert classify("walking_trail", None, None) == (PlaceEnvironment.OUTDOOR, "category_outdoor")
    assert classify("cafe", None, None) == (PlaceEnvironment.INDOOR, "category_indoor")
    assert classify("accommodation", None, None) == (PlaceEnvironment.INDOOR, "category_indoor")
    assert classify("pet_service", None, None) == (PlaceEnvironment.INDOOR, "category_indoor")


def test_attraction_uses_policy() -> None:
    assert classify("attraction", None, PetPolicyType.OUTDOOR_ONLY) == (
        PlaceEnvironment.OUTDOOR,
        "attraction_outdoor_only",
    )
    assert classify("attraction", None, PetPolicyType.INDOOR_ALLOWED) == (
        PlaceEnvironment.MIXED,
        "attraction_mixed",
    )
    assert classify("attraction", None, None) == (PlaceEnvironment.MIXED, "attraction_mixed")


def test_description_keywords_override_category() -> None:
    # 설명이 카테고리보다 강한 신호라 먼저 본다.
    assert classify("beach", "실내 전시관도 있음", None) == (
        PlaceEnvironment.INDOOR,
        "desc_indoor",
    )
    assert classify("cafe", "숲속 공원 옆", None) == (PlaceEnvironment.OUTDOOR, "desc_outdoor")
    # attraction 의 애매한 mixed 를 설명으로 좁힌다(승격).
    assert classify("attraction", "제주 자연사 박물관", PetPolicyType.INDOOR_ALLOWED) == (
        PlaceEnvironment.INDOOR,
        "desc_indoor",
    )


def test_indoor_keyword_wins_when_both_present() -> None:
    assert classify("attraction", "공원 안 박물관", None)[0] == PlaceEnvironment.INDOOR
