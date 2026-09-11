from scripts.extract_cuisine import parse_cuisine, within_match_radius


def test_parse_cuisine_takes_second_level() -> None:
    assert parse_cuisine("음식점 > 한식 > 해물,생선") == "한식"
    assert parse_cuisine("음식점 > 카페 > 커피전문점") == "카페"
    assert parse_cuisine("음식점 > 일식 > 초밥,롤") == "일식"


def test_parse_cuisine_rejects_non_food_category() -> None:
    assert parse_cuisine("가정,생활 > 애견,반려동물 > 애견카페") is None
    assert parse_cuisine("음식점") is None
    assert parse_cuisine("") is None


def test_within_match_radius() -> None:
    place = (33.4996, 126.5312)
    assert within_match_radius(place, (33.4997, 126.5313)) is True  # ~15m
    assert within_match_radius(place, (33.4000, 126.5000)) is False  # 수 km


def test_cuisine_length_is_capped() -> None:
    long_second = "가" * 40
    assert len(parse_cuisine(f"음식점 > {long_second} > 세부")) == 30
