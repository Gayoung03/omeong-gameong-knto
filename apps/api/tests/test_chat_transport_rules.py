"""운송 규정 판정 테스트.

**DB 없이 도는 테스트다.** 판정과 요금 계산은 순수 함수라 `TEST_DATABASE_URL`
없이도 돌아간다 — 여기가 틀리면 공항에서 탑승을 거부당하므로, 개발 환경에
따라 건너뛰어지면 안 된다.
"""

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

from app.db.models.enums import CarrierType
from app.integrations.llm.chat import _describe_rule
from app.rag.retrieval.guide_search import Verdict, _cargo_fee, _verdict

D = Decimal


def _rule(**overrides) -> SimpleNamespace:
    """`_cargo_fee` 가 보는 필드만 가진 가짜 규정."""
    base = {
        "cargo_fee_threshold_kg": D("32.00"),
        "cargo_fee_light_krw": 30000,
        "cargo_fee_heavy_krw": 60000,
    }
    return SimpleNamespace(**{**base, **overrides})


def _hit(**overrides):
    from app.rag.retrieval.guide_search import TransportRuleHit

    base = dict(
        carrier_name="대한항공",
        carrier_type=CarrierType.AIRLINE,
        route=None,
        cabin_allowed=True,
        cabin_max_weight_kg=D("7.00"),
        cabin_fee_krw=30000,
        cargo_allowed=True,
        cargo_max_weight_kg=D("45.00"),
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


class TestVerdict:
    def test_무게를_모르면_판정하지_않는다(self):
        # 사용자가 무게를 말하지 않았는데 "가능합니다"라고 단정하면 안 된다.
        assert _verdict(True, D("7.00"), None) is None

    def test_확인_안_된_것은_불가가_아니다(self):
        # cabin_allowed 가 None 이면 우리가 모르는 것이다. False 로 뭉개면
        # 없는 규정을 만들어 답하게 된다.
        assert _verdict(None, D("7.00"), D("5.0")) is Verdict.UNKNOWN

    def test_불가라고_명시된_것은_불가다(self):
        assert _verdict(False, None, D("5.0")) is Verdict.NOT_ALLOWED

    def test_상한과_같은_무게는_가능하다(self):
        # 경계값. 7kg 상한에 정확히 7kg 은 통과다(이하 기준).
        assert _verdict(True, D("7.00"), D("7.00")) is Verdict.ALLOWED

    def test_상한을_넘으면_무게_초과다(self):
        assert _verdict(True, D("7.00"), D("7.01")) is Verdict.OVER_WEIGHT

    def test_가능하지만_상한을_모르면_따로_표시한다(self):
        # "가능" 으로 답하면 무게 때문에 거절당할 수 있다는 걸 못 알린다.
        assert _verdict(True, None, D("12.0")) is Verdict.WEIGHT_UNKNOWN


class TestCargoFee:
    def test_기준_이하면_싼_쪽이다(self):
        assert _cargo_fee(_rule(), D("30.0")) == 30000

    def test_기준과_같으면_싼_쪽이다(self):
        assert _cargo_fee(_rule(), D("32.00")) == 30000

    def test_기준을_넘으면_비싼_쪽이다(self):
        assert _cargo_fee(_rule(), D("33.0")) == 60000

    def test_무게를_모르면_기본값을_준다(self):
        assert _cargo_fee(_rule(), None) == 30000


class TestDescribeRule:
    def test_값이_없는_항목은_빼고_보낸다(self):
        # null 을 그대로 넘기면 GPT 가 "없다 = 불가" 로 읽는다.
        described = _describe_rule(_hit())
        assert "pledge_required" not in described
        assert "duration_minutes" not in described
        assert "notes" not in described

    def test_불가라고_명시된_것은_남긴다(self):
        # False 는 "확인 안 됨" 이 아니라 "안 된다" 이므로 빠지면 안 된다.
        described = _describe_rule(_hit(cabin_allowed=False))
        assert described["cabin_allowed"] is False

    def test_확인일은_날짜까지만_준다(self):
        assert _describe_rule(_hit())["verified_at"] == "2026-08-26"

    def test_무게를_안_넣으면_판정_키가_없다(self):
        described = _describe_rule(_hit())
        assert "cabin_verdict" not in described
        assert "cargo_verdict" not in described

    def test_판정은_문자열로_나간다(self):
        described = _describe_rule(_hit(cabin_verdict=Verdict.OVER_WEIGHT))
        assert described["cabin_verdict"] == "무게 초과"

    def test_무게는_숫자로_바뀐다(self):
        # Decimal 은 json.dumps 가 직렬화하지 못한다.
        assert _describe_rule(_hit())["cabin_max_weight_kg"] == 7.0


class TestWeightConclusions:
    """회사마다 결론 문장을 통째로 만들어 보내는 부분.

    화면 확인에서 두 번 샜다 — 규정을 그대로 주면 "모두 화물칸에 실을 수 있다" 로
    묶었고, 분류만 주니 "기내 탑승이 불가하다" 로 뒤집어 적었다(실제로는 기내는
    되고 위탁이 없는 항공사였다). 여기가 틀리면 같은 오답이 돌아온다.
    """

    def test_기내_초과는_상한을_함께_말한다(self):
        from app.integrations.llm.chat import _weight_conclusions

        [result] = _weight_conclusions(
            [_hit(cabin_verdict=Verdict.OVER_WEIGHT, cargo_verdict=Verdict.ALLOWED)]
        )
        assert result["결론"] == "기내 불가(상한 7kg 초과), 위탁 가능"

    def test_위탁이_없는_것과_기내가_안_되는_것을_구분한다(self):
        # 제주항공은 기내는 되고(9kg) 위탁 제도가 없다. 이 둘을 뭉치면
        # "기내 탑승 불가" 라는 오답이 나온다.
        from app.integrations.llm.chat import _weight_conclusions

        [result] = _weight_conclusions(
            [
                _hit(
                    carrier_name="제주항공",
                    cabin_max_weight_kg=D("9.00"),
                    cabin_verdict=Verdict.OVER_WEIGHT,
                    cargo_verdict=Verdict.NOT_ALLOWED,
                )
            ]
        )
        assert result["결론"] == (
            "기내 불가(상한 9kg 초과), 위탁 제도 없음 → 이 회사로는 이 무게로 갈 수 없음"
        )

    def test_한쪽이라도_되면_갈_수_없다고_적지_않는다(self):
        from app.integrations.llm.chat import _weight_conclusions

        [result] = _weight_conclusions(
            [_hit(cabin_verdict=Verdict.OVER_WEIGHT, cargo_verdict=Verdict.ALLOWED)]
        )
        assert "갈 수 없음" not in result["결론"]

    def test_미확인은_갈_수_없다고_적지_않는다(self):
        # 확인 안 된 것을 불가로 뭉개면 없는 규정을 만들어 답하게 된다.
        from app.integrations.llm.chat import _weight_conclusions

        [result] = _weight_conclusions(
            [
                _hit(
                    carrier_name="한일고속페리",
                    cabin_max_weight_kg=None,
                    cargo_max_weight_kg=None,
                    cabin_verdict=Verdict.UNKNOWN,
                    cargo_verdict=Verdict.UNKNOWN,
                )
            ]
        )
        assert result["결론"] == "기내 가능 여부 미확인, 위탁 가능 여부 미확인"
        assert "갈 수 없음" not in result["결론"]

    def test_항로가_있으면_이름에_붙인다(self):
        from app.integrations.llm.chat import _weight_conclusions

        [result] = _weight_conclusions([_hit(carrier_name="씨월드고속훼리", route="목포-제주")])
        assert result["carrier"] == "씨월드고속훼리(목포-제주)"
