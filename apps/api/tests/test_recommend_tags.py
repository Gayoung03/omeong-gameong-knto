from app.recommend.config.tags import STANDARD_TAG_SET, STANDARD_TAGS, TAG_ORDER


def test_standard_tag_order_matches_database_contract() -> None:
    assert STANDARD_TAGS == ("바다", "카페", "산책", "포토스팟", "체험", "휴식", "실내관광")
    assert len(STANDARD_TAG_SET) == len(STANDARD_TAGS)
    assert TAG_ORDER is STANDARD_TAGS
