from app.recommend.config.tags import (
    STANDARD_TAG_SET,
    STANDARD_TAGS,
    TAG_LABELS,
    TAG_ORDER,
    normalize_preferred_tags,
)


def test_standard_tags_match_database_codes() -> None:
    # place_tags.code 7종(id 29~35). name 컬럼은 한글 라벨이며 TAG_LABELS 로 매핑.
    assert STANDARD_TAGS == (
        "sea",
        "cafe",
        "walk",
        "photo_spot",
        "experience",
        "rest",
        "indoor_tourism",
    )
    assert len(STANDARD_TAG_SET) == len(STANDARD_TAGS)
    assert TAG_ORDER is STANDARD_TAGS
    assert set(TAG_LABELS) == STANDARD_TAG_SET
    assert TAG_LABELS["sea"] == "바다"


def test_mobile_preference_labels_are_normalized_to_codes() -> None:
    assert normalize_preferred_tags(["바다·해변", "맛집", "카페", "바다·해변"]) == [
        "sea",
        "category:restaurant",
        "cafe",
    ]


def test_stored_korean_labels_and_codes_normalize_to_codes() -> None:
    # 과거 저장분(한글 라벨)과 이미 코드로 온 값이 섞여도 코드로 통일된다.
    assert normalize_preferred_tags(["바다", "sea", "실내관광"]) == ["sea", "indoor_tourism"]


def test_normalize_preferred_tags_is_idempotent() -> None:
    # 새 요청은 생성 시(endpoints/routes.py)와 추천 생성 시 두 번 정규화를 거친다.
    once = normalize_preferred_tags(["바다·해변", "바다", "sea", "실내관광"])
    assert normalize_preferred_tags(once) == once
