"""운송사별 제한 견종 적재 (ai-io-column-design 7.4 — "최우선" 백로그).

원자료는 **`docs/planning/travel-guide-collection.md`** — 각 운송사 공식 페이지에서
수집·전사된 목록이다("수집 규칙 1: 숫자·목록은 공식 페이지에서"). 웹에서 다시 긁지
않는 이유: 전사 오류 위험을 한 번(수집 문서)으로 묶어 두기 위해서다.
**규정이 바뀌면 그 문서와 여기 둘 다 고친다** (seed_guides 와 같은 관례).

- 목록은 문서의 `·` 구분 원문을 그대로 담고 프로그램이 쪼갠다 — 옮겨 적다 틀리는 것을
  줄이고, 종수는 문서가 명시한 수와 대조 검증한다(단위 테스트).
- **목록을 합치지 않는다** (table-reference: 도베르만은 제주항공에만 있다).
- 티웨이·이스타는 원문이 예시만 들어 `is_example_only=True` — 확정 목록처럼 보여주면
  안 되는 데이터임을 행 자체가 말한다.
- 에어부산 단두종·여객선 3사(한일·씨월드·아리온) 견종 제한은 **원문에 없다 → 넣지
  않는다** (과보정 금지 — 근거 없는 행 주입이 더 위험하다).
- 멱등: `(rule, breed_name_ko, restriction_type)` 존재 시 건너뜀 + 같은 조합 DB
  UNIQUE(f3a9c1d47b02). 유형까지 키인 이유: 아시아나 원문은 마스티프를 맹견·단두종
  양쪽에 올린다 — 이름만으로 막으면 정당한 행이 막힌다(리허설 실측).
- 기본 dry-run, `--apply` 로 반영.

실행:
    uv run python -m scripts.seed_restricted_breeds            # dry-run
    uv run python -m scripts.seed_restricted_breeds --apply    # 반영
"""

import sys
import uuid

from sqlalchemy import select

from app.db.models import TransportPetRule, TransportRestrictedBreed
from app.db.models.enums import BreedRestrictionScope, BreedRestrictionType
from app.db.session import SessionLocal

DANGEROUS = BreedRestrictionType.DANGEROUS
BRACHY = BreedRestrictionType.BRACHYCEPHALIC
CABIN = BreedRestrictionScope.CABIN
CARGO = BreedRestrictionScope.CARGO
BOTH = BreedRestrictionScope.BOTH


def split_breeds(raw: str) -> list[str]:
    """수집 문서의 `·` 구분 원문 → 견종명 목록. 괄호 주석은 이름의 일부로 유지한다."""
    return [name.strip() for name in raw.split("·") if name.strip()]


# (운송사 매칭 키, 제한 유형, 적용 구간, 예시 여부, 문서가 명시한 종수, `·` 원문)
# 원문 줄은 travel-guide-collection.md 에서 그대로 가져온다 — 임의 수정 금지.
BREED_GROUPS: list[tuple[tuple[str, str | None], BreedRestrictionType,
                         BreedRestrictionScope, bool, int | None, str]] = [
    # ── 대한항공 — 맹견은 전 구간, 단두종은 위탁만 불가(기내 조건 충족 시 기내 가능) ──
    (("대한항공", None), DANGEROUS, BOTH, False, 8,
     "도사견 · 핏불테리어 · 로트와일러 · 마스티프 · 라이카 · 오브차카 · 캉갈 · 울프독"),
    (("대한항공", None), BRACHY, CARGO, False, None,
     "뉴펀들랜드 · 도고 아르헨티노 · 도그 드 보르도 · 라사압소 · 보스턴 테리어 · 복서 · 불독 · "
     "브뤼셀 그리폰 · 샤페이 · 스패니얼(잉글리쉬 토이) · 시추 · 아메리칸 불리 · 아펜핀셔 · "
     "치와와 · 재패니스 친 · 차우차우 · 카네코르소 · 킹 찰스 스패니얼 · "
     "카발리에 킹 찰스 스패니얼 · 퍼그 · 페키니즈 · 티베탄 스패니얼"),
    (("대한항공", None), BRACHY, CARGO, False, None,
     "버미스 · 브리티쉬 숏헤어 · 스코티쉬 폴드 · 엑조틱 · 페르시안 · 히말라얀"),
    # ── 아시아나 — 맹견 12종, 단두종은 위탁 운송 중단(2019-07-01부) ──
    (("아시아나항공", None), DANGEROUS, BOTH, False, 12,
     "도사견 · 아메리칸 핏불테리어 · 아메리칸 스태퍼드셔 테리어 · 스태퍼드셔 불테리어 · "
     "로트와일러 · 마스티프 · 라이카 · 오브차카 · 캉갈 · 울프독 · "
     "아메리칸 불리/카네코르소 등 유사 견종 · 미니어쳐 불테리어"),
    (("아시아나항공", None), BRACHY, CARGO, False, None,
     "아펜핀셔 · 도고 아리젠티노 · 마스티프 · 보스턴 테리어 · 복서 · 불도그 · 브뤼셀 그리펀 · "
     "시추 · 스패니얼(잉글리쉬 토이, 킹 찰스 스패니얼, 티베탄) · 치와와 · 재퍼니스친 · "
     "라사압소 · 프레사 까나리오 · 차우차우 · 퍼그 · 페키니즈 · 샤페이 · 카네코르소 · "
     "도그 드 보르도"),
    (("아시아나항공", None), BRACHY, CARGO, False, None,
     "버미스 · 엑조틱 · 히말라얀 · 페르시안 · 브리티쉬 숏헤어 · 스코티쉬 폴드 · 실버 친칠라"),
    # ── 제주항공 — 위탁이 없어 목록이 기내 기준. 도베르만은 여기에만 있다 ──
    (("제주항공", None), DANGEROUS, CABIN, False, 15,
     "도사견 · 아메리칸 핏불테리어 · 아메리칸 스태퍼드셔 테리어 · 스태퍼드셔 불테리어 · "
     "불테리어 · 로트와일러 · 마스티프 · 라이카 · 오브차카(코카시안 셰퍼드 독) · 캉갈 · "
     "울프독 · 도베르만 · 미니어쳐 불테리어 · 아메리칸 불리 · 카네코르소"),
    # ── 진에어 — 맹견 10종 전 구간, 단두종은 위탁 불가 ──
    (("진에어", None), DANGEROUS, BOTH, False, 10,
     "도사견 · 아메리칸 핏불테리어 · 아메리칸 스태퍼드셔 테리어 · 스태퍼드셔 불테리어 · "
     "로트와일러 · 마스티프 · 라이카 · 오브차카(코카시안 셰퍼드 독) · "
     "캉갈(아나톨리언 셰퍼드 독) · 울프독"),
    (("진에어", None), BRACHY, CARGO, False, 20,
     "아펜핀셔 · 아메리칸 불리 · 보스턴 테리어 · 복서 · 브뤼셀 그리폰 · 불독(전 품종) · "
     "카네코르소 · 치와와 · 차우차우 · 도고 아르헨티노 · 도그 드 보르도 · "
     "잉글리쉬 토이 스패니얼(킹 찰스 스패니얼) · 재패니스 친 · 라사압소 · 뉴펀들랜드 · "
     "페키니즈 · 퍼그(전 품종) · 샤페이 · 시추 · 티베탄 스패니얼"),
    (("진에어", None), BRACHY, CARGO, False, 6,
     "버미스 · 브리티쉬 쇼트헤어 · 엑조틱 · 히말라얀 · 페르시안 · 스코티시 폴드"),
    # ── 에어부산 — 맹견 12종 (아시아나와 동일 목록·같은 계열). 단두종 명시 없음 → 미적재 ──
    (("에어부산", None), DANGEROUS, BOTH, False, 12,
     "도사견 · 아메리칸 핏불테리어 · 아메리칸 스태퍼드셔 테리어 · 스태퍼드셔 불테리어 · "
     "로트와일러 · 마스티프 · 라이카 · 오브차카 · 캉갈 · 울프독 · "
     "아메리칸 불리/카네코르소 등 유사 견종 · 미니어쳐 불테리어"),
    # ── 티웨이 — 원문이 예시만 든다("~과 같은 투기견 종") → is_example_only ──
    (("티웨이항공", None), DANGEROUS, BOTH, True, None,
     "아메리칸 핏불테리어 · 로트와일러 · 도베르만"),
    # ── 이스타 — 예시 + 동물보호법 시행규칙 맹견류 준용 → is_example_only ──
    (("이스타항공", None), DANGEROUS, CABIN, True, None,
     "아메리칸 핏불 테리어 · 도베르만 · 로트와일러 · 투견"),
    # ── 오션비스타제주 — 운송금지견종 8종("~류" 표기 그대로) ──
    (("오션비스타제주", "삼천포↔제주"), DANGEROUS, BOTH, False, 8,
     "도사견류 · 핏불테리어류 · 로트와일러류 · 마스티프류 · 라이카류 · 오브차가류 · "
     "캉갈류 · 울프독류"),
]


def main() -> None:
    apply = "--apply" in sys.argv[1:]

    with SessionLocal() as db:
        rules = {
            (rule.carrier_name, rule.route): rule
            for rule in db.scalars(select(TransportPetRule)).all()
        }
        existing = {
            (row.transport_pet_rule_id, row.breed_name_ko, row.restriction_type)
            for row in db.scalars(select(TransportRestrictedBreed)).all()
        }

        planned = skipped = 0
        for key, r_type, scope, example, declared, raw in BREED_GROUPS:
            rule = rules.get(key)
            if rule is None:
                raise SystemExit(f"규정 행을 찾지 못했습니다: {key} — seed_guides 먼저 실행하세요.")
            names = split_breeds(raw)
            if declared is not None and len(names) != declared:
                raise SystemExit(
                    f"{key} {r_type.value}: 문서 명시 {declared}종 ≠ "
                    f"파싱 {len(names)}종 — 전사 확인"
                )
            for name in names:
                key3 = (rule.id, name, r_type)
                if key3 in existing:
                    skipped += 1
                    continue
                existing.add(key3)  # 같은 실행 안의 중복도 막는다
                planned += 1
                print(f"  {key[0]} [{r_type.value}/{scope.value}"
                      f"{'/예시' if example else ''}] {name}")
                if apply:
                    db.add(
                        TransportRestrictedBreed(
                            id=uuid.uuid4(),
                            transport_pet_rule_id=rule.id,
                            breed_name_ko=name,
                            restriction_type=r_type,
                            applies_to=scope,
                            is_example_only=example,
                        )
                    )
        if apply:
            db.commit()

    mode = "적용" if apply else "DRY-RUN"
    print(f"{mode}: {planned}건 추가 대상 / 이미 있음 {skipped}건")
    if not apply:
        print("실제 반영하려면 --apply 를 붙여 다시 실행하세요.")


if __name__ == "__main__":
    main()