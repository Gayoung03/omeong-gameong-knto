"""겸업 카테고리 확장 테스트.

**DB 없이 도는 테스트다.** 이 저장소는 `TEST_DATABASE_URL` 이 없으면 DB 테스트를
건너뛰는데, 카테고리 확장이 틀리면 **"식당 알려줘"에 한 곳만 나오는** 상태로
되돌아간다. 개발 환경에 따라 건너뛰어지면 안 돼서 순수 함수로 분리해 두고
여기서 검증한다(운송 규정의 무게 판정과 같은 이유).
"""

from app.rag.retrieval.place_search import _CATEGORY_ALIASES, _expand_category
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
