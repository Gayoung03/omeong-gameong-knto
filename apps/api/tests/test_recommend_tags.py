from app.recommend.config.tags import (
    STANDARD_TAG_SET,
    STANDARD_TAGS,
    TAG_ORDER,
    normalize_preferred_tags,
)


def test_standard_tag_order_matches_database_contract() -> None:
    assert STANDARD_TAGS == ("바다", "카페", "산책", "포토스팟", "체험", "휴식", "실내관광")
    assert len(STANDARD_TAG_SET) == len(STANDARD_TAGS)
    assert TAG_ORDER is STANDARD_TAGS


def test_mobile_preference_labels_are_normalized_for_the_engine() -> None:
    assert normalize_preferred_tags(["바다·해변", "맛집", "카페", "바다·해변"]) == [
        "바다",
        "category:restaurant",
        "카페",
    ]
