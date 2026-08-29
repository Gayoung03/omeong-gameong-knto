"""겸업 카테고리 확장 테스트.

**DB 없이 도는 테스트다.** 이 저장소는 `TEST_DATABASE_URL` 이 없으면 DB 테스트를
건너뛰는데, 카테고리 확장이 틀리면 **"식당 알려줘"에 한 곳만 나오는** 상태로
되돌아간다. 개발 환경에 따라 건너뛰어지면 안 돼서 순수 함수로 분리해 두고
여기서 검증한다(운송 규정의 무게 판정과 같은 이유).
"""

from app.rag.retrieval.place_search import (
    _CATEGORY_ALIASES,
    _EXCLUDED_WITHOUT_CATEGORY,
    _expand_category,
)
from app.rag.vocabulary import CATEGORIES


class Test겸업확장:
    def test_식당은_식당겸카페까지_함께_본다(self):
        assert set(_expand_category("restaurant")) == {"restaurant", "restaurant_cafe"}

    def test_카페도_식당겸카페까지_함께_본다(self):
        assert set(_expand_category("cafe")) == {"cafe", "restaurant_cafe"}

    def test_겸업_자체를_고르면_그대로_본다(self):
        assert _expand_category("restaurant_cafe") == ("restaurant_cafe",)

    def test_겸업이_없는_카테고리는_넓히지_않는다(self):
        for code in ("accommodation", "attraction", "beach", "oreum"):
            assert _expand_category(code) == (code,)


class Test확장표가_어휘와_어긋나지_않는다:
    """확장한 값이 `places.category` 에 없는 문자열이면 검색이 조용히 0건이 된다."""

    def test_확장_결과는_전부_실제_카테고리_값이다(self):
        for code in CATEGORIES:
            for expanded in _expand_category(code):
                assert expanded in CATEGORIES

    def test_어떤_카테고리도_자기_자신을_잃지_않는다(self):
        for code in CATEGORIES:
            assert code in _expand_category(code)

    def test_확장표의_열쇠도_어휘_목록_안에_있다(self):
        for code in _CATEGORY_ALIASES:
            assert code in CATEGORIES


class Test카테고리를_안_집었을_때_빼는_것:
    """`"강아지랑 갈 실내 장소"` 에 **동물약국**이 추천된 것을 화면에서 확인했다(2026-08-29).

    `etc` 278건은 여행지가 아니라 반려동물 인프라(약국·병원·용품·미용)다.
    `vocabulary.py` 에서 뺀 것은 **모델이 고를 수 없게** 한 것일 뿐이라,
    카테고리를 안 넘긴 검색에는 그대로 섞여 나왔다.
    """

    def test_etc_를_뺀다(self):
        assert "etc" in _EXCLUDED_WITHOUT_CATEGORY

    def test_빼는_것은_어휘에_없어야_한다(self):
        """어휘에 있으면 모델이 고를 수 있는 값인데 기본 검색에서만 사라져 헷갈린다.

        `etc` 152건 재분류가 끝나 어휘에 들어오면 이 목록에서도 빠져야 한다.
        """
        for code in _EXCLUDED_WITHOUT_CATEGORY:
            assert code not in CATEGORIES

    def test_겸업_확장표와_겹치지_않는다(self):
        """확장으로 넣은 것을 다시 빼면 서로를 무효로 만든다."""
        expanded = {code for values in _CATEGORY_ALIASES.values() for code in values}
        assert expanded.isdisjoint(_EXCLUDED_WITHOUT_CATEGORY)
