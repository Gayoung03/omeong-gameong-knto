"""견종 제한 대조 테스트.

**DB 없이 도는 테스트다.** 대조와 결론 문장은 순수 함수라 `TEST_DATABASE_URL`
없이도 돌아간다 — 여기가 틀리면 제한 대상인 아이를 "가능"으로 안내하게 되므로,
개발 환경에 따라 건너뛰어지면 안 된다.

2026-09-13 측정에서 `"복서 데리고 제주도 갈 수 있나요?"` 8회(모델 둘 × 4회)가
**전부** 근거 없이 분류했다. 원인은 `search_transport_rules` 가 견종을 아예 읽지
않은 것이었다(팀 dev RDS 에 152건이 있는데도). 그 구멍을 막은 코드가 여기다.
"""

from datetime import UTC, datetime
from decimal import Decimal

from app.db.models.enums import BreedRestrictionScope, BreedRestrictionType, CarrierType
from app.integrations.llm.chat import _breed_conclusions, _breed_phrase
from app.rag.retrieval.guide_search import (
    BreedCheck,
    BreedMatch,
    TransportRuleHit,
    breed_matches,
)

D = Decimal
DANGEROUS = BreedRestrictionType.DANGEROUS
BRACHY = BreedRestrictionType.BRACHYCEPHALIC


def _match(**overrides) -> BreedMatch:
    base = dict(
        breed_name_ko="복서",
        restriction_type=BRACHY,
        applies_to=BreedRestrictionScope.CARGO,
        is_example_only=False,
    )
    return BreedMatch(**{**base, **overrides})


def _check(matches=(), listed=(), example_only=(), query="복서") -> BreedCheck:
    return BreedCheck(
        query=query,
        matches=tuple(matches),
        listed_types=frozenset(listed),
        example_only_types=frozenset(example_only),
    )


def _hit(**overrides) -> TransportRuleHit:
    base = dict(
        carrier_name="대한항공",
        carrier_type=CarrierType.AIRLINE,
        route=None,
        cabin_allowed=True,
        cabin_max_weight_kg=D("7.00"),
        cabin_weight_unlimited=None,
        cabin_conditions=None,
        cabin_fee_krw=30000,
        cargo_allowed=True,
        cargo_max_weight_kg=D("45.00"),
        cargo_weight_unlimited=None,
        cargo_fee_krw=30000,
        same_day_request_allowed=None,
        request_deadline_hours=24,
        pledge_required=None,
        duration_minutes=None,
        notes=None,
        source_url=None,
        verified_at=datetime(2026, 8, 26, tzinfo=UTC),
    )
    return TransportRuleHit(**{**base, **overrides})


class TestBreedMatches:
    def test_같은_이름은_맞는다(self):
        assert breed_matches("복서", "복서")

    def test_괄호_주석은_떼고_본다(self):
        # 원문이 `불독(전 품종)`, `퍼그(전 품종)` 처럼 괄호를 단다.
        assert breed_matches("불독", "불독(전 품종)")

    def test_공백_차이는_무시한다(self):
        assert breed_matches("보스턴테리어", "보스턴 테리어")

    def test_표기_차이는_대표_이름으로_모은다(self):
        # 대한항공은 `불독`, 아시아나는 `불도그` 다. 글자만 맞대면 아시아나에서
        # 제한 대상인 아이가 "목록에 없음" 으로 새어 나간다 — 가장 위험한 방향이다.
        assert breed_matches("불독", "불도그")
        assert breed_matches("불도그", "불독")
        assert breed_matches("시츄", "시추")
        assert breed_matches("재패니스 친", "재퍼니스친")
        assert breed_matches("브뤼셀 그리폰", "브뤼셀 그리펀")

    def test_류로_묶어_적은_원문도_맞춘다(self):
        # 오션비스타제주 원문이 `도사견류 · 핏불테리어류` 로 적는다.
        assert breed_matches("도사견", "도사견류")

    def test_부분_일치로_번지지_않는다(self):
        # `불독` 이 `불테리어` 에 걸리면 제한이 없는 아이를 제한 대상으로 만든다.
        assert not breed_matches("불독", "불테리어")
        assert not breed_matches("테리어", "보스턴 테리어")
        assert not breed_matches("푸들", "복서")

    def test_빈_이름은_아무것도_맞추지_않는다(self):
        assert not breed_matches("", "복서")
        assert not breed_matches("   ", "복서")


class TestBreedCheckStatus:
    def test_목록에_있으면_제한이다(self):
        assert _check(matches=[_match()], listed=[BRACHY]).status(BRACHY) == "제한"

    def test_목록을_공개했는데_없으면_목록에없음이다(self):
        assert _check(listed=[DANGEROUS]).status(DANGEROUS) == "목록에없음"

    def test_목록_자체가_없으면_확인불가다(self):
        # 에어부산은 단두종 목록이 원문에 없다. "없으니 가능" 이 아니다.
        assert _check(listed=[DANGEROUS]).status(BRACHY) == "확인불가"

    def test_예시만_있으면_확인불가다(self):
        # 티웨이·이스타 원문은 `~과 같은 투기견 종` 으로 예시만 든다.
        # 거기 없다고 "제한 없음" 이라고 말할 수 없다.
        assert _check(example_only=[DANGEROUS]).status(DANGEROUS) == "확인불가"


class TestBreedPhrase:
    def test_제한은_적용_구간까지_말한다(self):
        phrase = _breed_phrase(_check(matches=[_match()], listed=[DANGEROUS, BRACHY]))
        assert phrase == "맹견 목록에는 없음 · 단두종 목록에 있음 → 위탁 불가"

    def test_전_구간_제한은_그렇게_적는다(self):
        phrase = _breed_phrase(
            _check(
                matches=[_match(restriction_type=DANGEROUS, applies_to=BreedRestrictionScope.BOTH)],
                listed=[DANGEROUS],
            )
        )
        assert "맹견 목록에 있음 → 기내·위탁 모두 불가" in phrase

    def test_예시_목록에_걸린_것은_그렇게_밝힌다(self):
        phrase = _breed_phrase(
            _check(
                matches=[
                    _match(
                        breed_name_ko="도베르만",
                        restriction_type=DANGEROUS,
                        applies_to=BreedRestrictionScope.BOTH,
                        is_example_only=True,
                    )
                ],
                example_only=[DANGEROUS],
                query="도베르만",
            )
        )
        assert "(원문이 예시로만 든 목록)" in phrase

    def test_확인_안_됨을_가능으로_바꾸지_않는다(self):
        phrase = _breed_phrase(_check(listed=[DANGEROUS]))
        assert phrase == "맹견 목록에는 없음 · 단두종 목록이 공개되지 않아 확인 안 됨"
        assert "가능" not in phrase


class TestBreedConclusions:
    def test_견종을_안_넣으면_결론이_없다(self):
        assert _breed_conclusions([_hit()]) == []

    def test_위탁_제도가_없는_곳은_견종과_무관함을_먼저_말한다(self):
        # 제주항공·티웨이·이스타. 견종 이야기로 넘어가기 전에 제도부터 갈라야
        # "단두종이라 안 된다" 로 잘못 묶이지 않는다.
        [result] = _breed_conclusions(
            [
                _hit(
                    carrier_name="제주항공",
                    cargo_allowed=False,
                    breed_check=_check(listed=[DANGEROUS]),
                )
            ]
        )
        assert result["결론"].startswith("위탁 제도 자체가 없어 견종과 무관하게 위탁 불가")

    def test_세_갈래가_한_조회_안에서_구분된다(self):
        # 2026-09-13 설계 문서가 목표로 적은 답변 모양 그대로다.
        results = _breed_conclusions(
            [
                _hit(
                    carrier_name="대한항공",
                    breed_check=_check(matches=[_match()], listed=[DANGEROUS, BRACHY]),
                ),
                _hit(carrier_name="에어부산", breed_check=_check(listed=[DANGEROUS])),
                _hit(
                    carrier_name="제주항공",
                    cargo_allowed=False,
                    breed_check=_check(listed=[DANGEROUS]),
                ),
            ]
        )
        by_carrier = {r["carrier"]: r["결론"] for r in results}
        assert "단두종 목록에 있음 → 위탁 불가" in by_carrier["대한항공"]
        assert "단두종 목록이 공개되지 않아 확인 안 됨" in by_carrier["에어부산"]
        assert by_carrier["제주항공"].startswith("위탁 제도 자체가 없어")

    def test_항로가_있으면_이름에_붙인다(self):
        [result] = _breed_conclusions(
            [
                _hit(
                    carrier_name="오션비스타제주",
                    route="삼천포↔제주",
                    breed_check=_check(listed=[DANGEROUS]),
                )
            ]
        )
        assert result["carrier"] == "오션비스타제주(삼천포↔제주)"
