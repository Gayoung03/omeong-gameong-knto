from app.db.models.enums import PetPolicyType, PlaceEnvironment
from scripts.backfill_place_environment import classify


def test_category_rules_ignore_description() -> None:
    assert classify("beach", None, None) == (PlaceEnvironment.OUTDOOR, "category_outdoor")
    assert classify("oreum", None, None) == (PlaceEnvironment.OUTDOOR, "category_outdoor")
    assert classify("walking_trail", None, None) == (PlaceEnvironment.OUTDOOR, "category_outdoor")
    assert classify("cafe", None, None) == (PlaceEnvironment.INDOOR, "category_indoor")
    assert classify("accommodation", None, None) == (PlaceEnvironment.INDOOR, "category_indoor")
    assert classify("pet_service", None, None) == (PlaceEnvironment.INDOOR, "category_indoor")
    # 카테고리로 확실한 곳은 설명 키워드로 뒤집지 않는다.
    assert classify("cafe", "숲속 공원 옆 카페", None) == (
        PlaceEnvironment.INDOOR,
        "category_indoor",
    )
    assert classify("beach", "실내 전시관도 있음", None) == (
        PlaceEnvironment.OUTDOOR,
        "category_outdoor",
    )


def test_attraction_description_indoor() -> None:
    for keyword in ("실내", "박물관", "전시", "미술관", "기념관", "체험관"):
        assert classify("attraction", f"제주 {keyword} 공간", None) == (
            PlaceEnvironment.INDOOR,
            "attraction_desc_indoor",
        )


def test_attraction_description_outdoor() -> None:
    for keyword in ("해변", "오름", "숲", "공원", "정원", "목장", "해안"):
        assert classify("attraction", f"{keyword} 산책", None) == (
            PlaceEnvironment.OUTDOOR,
            "attraction_desc_outdoor",
        )


def test_attraction_falls_back_to_policy_then_mixed() -> None:
    assert classify("attraction", None, PetPolicyType.OUTDOOR_ONLY) == (
        PlaceEnvironment.OUTDOOR,
        "attraction_outdoor_only",
    )
    assert classify("attraction", None, PetPolicyType.INDOOR_ALLOWED) == (
        PlaceEnvironment.MIXED,
        "attraction_mixed",
    )
    assert classify("attraction", None, None) == (PlaceEnvironment.MIXED, "attraction_mixed")


def test_attraction_indoor_keyword_wins_over_outdoor() -> None:
    assert classify("attraction", "공원 안 박물관", None)[0] == PlaceEnvironment.INDOOR
