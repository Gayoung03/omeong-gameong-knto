from scripts.audit_category_pollution import CONFIRMED_CORRECTIONS, proposed_target


def test_accommodation_keywords_map_to_accommodation() -> None:
    names = (
        "애월해변펜션",
        "제주스테이",
        "오션하우스",
        "협재게스트하우스",
        "중문리조트",
        "바다숙소",
    )
    for name in names:
        target, _ = proposed_target(name)
        assert target == "accommodation"


def test_cafe_keyword_maps_to_cafe() -> None:
    assert proposed_target("해변뷰카페") == ("cafe", "카페")


def test_accommodation_keyword_wins_over_cafe() -> None:
    # 앞선 키워드(숙소 계열)를 먼저 잡는다.
    assert proposed_target("펜션카페")[0] == "accommodation"


def test_plain_name_has_no_proposal() -> None:
    assert proposed_target("협재해수욕장") is None
    assert proposed_target("사려니숲길") is None


def test_confirmed_corrections_targets_are_valid() -> None:
    names = [name for name, _ in CONFIRMED_CORRECTIONS]
    assert names == ["성산풀하우스", "이리로스테이", "바다스케치", "제주에코스위츠", "심바카레"]
    valid = {"accommodation", "cafe", "restaurant"}
    assert all(target in valid for _, target in CONFIRMED_CORRECTIONS)
