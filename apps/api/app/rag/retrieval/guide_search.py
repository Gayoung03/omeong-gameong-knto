"""챗봇이 부르는 여행 가이드·운송 규정 검색.

`place_search.py` 와 같은 방식이다 — GPT 는 우리 테이블을 볼 수 없으므로 **답변을
만들기 전에 우리가 먼저 찾아 재료로 건네준다.**

## 도구를 둘로 나눈 이유

설계 결정 B3 은 도구를 `search_places` · `search_guides` 둘로 잡았지만, 가이드 쪽
데이터는 성격이 다른 두 벌이다.

- `guide_documents` — 사람이 **읽는 글**. 준비물, 제주 입도 절차, 렌터카
- `transport_pet_rules` — **숫자로 거르는 값**. 무게 상한, 요금, 신청 기한

`"12kg 인데 기내 되나요"` 는 숫자 비교라 글 검색으로 답이 나오지 않는다. 하나로 합치면
GPT 가 언제 무게를 넘겨야 하는지 헷갈려 하므로 **`search_transport_rules` 를 따로 둔다.**

## 판정을 파이썬에서 한다

무게 비교(`12 > 7`)를 GPT 에게 맡기지 않는다. 모델은 숫자 비교를 곧잘 틀리고, 여기서
틀리면 **공항에서 탑승을 거부당한다.** 우리가 `cabin_verdict` 로 결론을 내서 넘기고,
GPT 는 그 결론을 문장으로 옮기기만 한다.

## `None` 을 `False` 로 뭉개지 않는다

`TransportPetRule` 의 boolean 은 전부 nullable 이다(모델 주석 참고).

- `True` — 가능하다고 명시됨
- `False` — **불가라고 명시됨**
- `None` — **확인 안 됨**

셋을 둘로 줄이면 "확인 안 된 것"이 "불가"가 되어 없는 규정을 만들어 답하게 된다.
판정에도 `UNKNOWN` 을 그대로 남긴다(설계 결정 A7).

## 견종도 같은 이유로 파이썬에서 대조한다

`transport_restricted_breeds` 에 회사별 제한 견종이 있는데(팀 dev RDS 152건)
**챗봇 도구가 그걸 읽지 않고 있었다.** 앱의 `/guides` 는 읽는다. 그래서 챗봇은
아는 것을 모른다고 답하거나 지레짐작했다 — 2026-09-13 측정에서 `"복서"` 질문
8회 전부 근거 없이 분류했다.

무게와 똑같이 **대조를 여기서 하고 회사별 결론만 건넨다.** 그리고 세 가지를
절대 섞지 않는다.

1. **목록에 있음** — 그 회사가 명시한 제한 대상이다
2. **목록에는 없음** — 그 회사가 목록을 공개했고 거기 없다
3. **목록이 없어 확인 안 됨** — 목록 자체가 없거나(에어부산 단두종) 예시만
   공개된 경우(티웨이·이스타)다. **이것을 "가능"으로 바꾸면 안 된다.**
"""

import re
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.models.enums import (
    BreedRestrictionScope,
    BreedRestrictionType,
    CarrierType,
    GuideCategory,
)
from app.db.models.guides import (
    GuideDocument,
    GuideDocumentSource,
    TransportPetRule,
    TransportRestrictedBreed,
)

#: 가이드 글은 한 편이 400~1100자로 짧다. 두 편이면 답변 근거로 충분하다.
DEFAULT_GUIDE_LIMIT = 2
MAX_GUIDE_LIMIT = 3

#: 운송사는 항공사 7곳 + 여객선 4항로가 전부다. 종류를 좁히면 한 번에 다 줘도 된다.
MAX_RULE_LIMIT = 12


class Verdict(StrEnum):
    """무게를 넣었을 때의 판정.

    `UNKNOWN` 과 `NOT_ALLOWED` 는 반드시 구분한다 — 앞은 "우리가 모른다",
    뒤는 "규정이 안 된다고 한다"이다.
    """

    ALLOWED = "가능"
    NOT_ALLOWED = "불가"
    OVER_WEIGHT = "무게 초과"
    WEIGHT_UNKNOWN = "가능하나 무게 기준 미확인"
    UNKNOWN = "확인 안 됨"


@dataclass(frozen=True)
class GuideHit:
    """가이드 글 한 편과 그 출처.

    `sources` 와 `verified_at` 을 **반드시 함께 들고 다닌다.** 규정은 자주 바뀌어서
    "언제 기준인지"가 빠지면 답변이 오래된 정보를 단정하는 꼴이 된다(설계 결정 A6).
    """

    slug: str
    title: str
    category: GuideCategory
    body: str
    sources: tuple[tuple[str, str | None], ...]
    verified_at: datetime | None


_BREED_PAREN = re.compile(r"[（(][^）)]*[）)]")
_BREED_NOISE = re.compile(r"등\s*유사\s*견종")

#: 같은 견종의 **표기 차이**. 운송사 원문이 제각각이라(대한항공 `불독` /
#: 아시아나 `불도그`) 글자만 맞대면 제한 대상인 아이를 "목록에 없음"으로 흘려보낸다.
#: 그 방향의 오답이 제일 위험하다 — 안 되는 것을 된다고 읽히게 한다.
#: **우리 씨앗 데이터(`scripts/seed_restricted_breeds.py`)에 실제로 있는 차이만** 담는다.
BREED_ALIASES = {
    "불도그": "불독",
    "시츄": "시추",
    "재퍼니스친": "재패니스친",
    "브뤼셀그리펀": "브뤼셀그리폰",
    "도고아리젠티노": "도고아르헨티노",
    "스코티시폴드": "스코티쉬폴드",
    "브리티쉬쇼트헤어": "브리티쉬숏헤어",
    "오브차가": "오브차카",
}


def _normalize_breed(name: str) -> str:
    """견종 이름을 비교할 수 있는 형태로.

    괄호 주석(`불독(전 품종)`)·공백·`등 유사 견종` 을 떼고 표기 차이를 대표 이름으로
    모은다. `~류`(`도사견류`)는 여기서 떼지 않고 매칭 쪽에서 따로 본다.
    """
    text = _BREED_NOISE.sub("", _BREED_PAREN.sub("", name))
    text = re.sub(r"\s+", "", text).casefold()
    return BREED_ALIASES.get(text, text)


def breed_matches(query: str, entry: str) -> bool:
    """사용자가 말한 견종이 목록 항목과 같은 것인가.

    **부분 일치를 쓰지 않는다.** `불독` 이 `불테리어` 에 걸리거나 `테리어` 가 모든
    테리어를 쓸어담으면 제한이 없는 아이를 제한 대상으로 만든다 — 반대 방향이지만
    이것도 오답이다. 원문에 실제로 있는 형태만 맞춘다.
    """
    normalized = _normalize_breed(query)
    if not normalized:
        return False
    for part in _normalize_breed(entry).split("/"):
        if part == normalized:
            return True
        # `도사견류` 처럼 원문이 `~류` 로 묶어 적은 경우.
        if part.endswith("류") and part[:-1] == normalized:
            return True
    return False


@dataclass(frozen=True)
class BreedMatch:
    """이 견종이 걸린 목록 항목 하나."""

    breed_name_ko: str
    restriction_type: BreedRestrictionType
    applies_to: BreedRestrictionScope
    is_example_only: bool


@dataclass(frozen=True)
class BreedCheck:
    """한 운송사에서 이 견종이 어디에 걸리는지.

    **걸린 것과 "걸린 게 없다"를 구분해서 담는다.** 목록에 없다는 것과 목록 자체가
    없다는 것은 전혀 다른 말인데, 하나로 뭉치면 후자가 "가능"으로 읽힌다.
    """

    query: str
    matches: tuple[BreedMatch, ...]
    #: 그 회사가 **확정 목록**을 공개한 제한 유형.
    listed_types: frozenset[BreedRestrictionType]
    #: 원문이 예시만 든 제한 유형(`is_example_only`). 없는 것을 없다고 말할 수 없다.
    example_only_types: frozenset[BreedRestrictionType]

    def status(self, restriction_type: BreedRestrictionType) -> str:
        """`제한` / `목록에없음` / `확인불가` 중 하나."""
        if any(match.restriction_type is restriction_type for match in self.matches):
            return "제한"
        if restriction_type in self.example_only_types:
            return "확인불가"
        return "목록에없음" if restriction_type in self.listed_types else "확인불가"


@dataclass(frozen=True)
class TransportRuleHit:
    """운송사 한 곳의 반려동물 규정.

    무게를 넣어 부르면 `cabin_verdict` · `cargo_verdict` 가 채워진다.
    넣지 않으면 `None` 이고, 규정 값만 그대로 나간다.
    """

    carrier_name: str
    carrier_type: CarrierType
    route: str | None
    cabin_allowed: bool | None
    cabin_max_weight_kg: Decimal | None
    cabin_weight_unlimited: bool | None
    cabin_conditions: str | None
    cabin_fee_krw: int | None
    cargo_allowed: bool | None
    cargo_max_weight_kg: Decimal | None
    cargo_weight_unlimited: bool | None
    cargo_fee_krw: int | None
    same_day_request_allowed: bool | None
    request_deadline_hours: int | None
    pledge_required: bool | None
    duration_minutes: int | None
    notes: str | None
    source_url: str | None
    verified_at: datetime | None
    cabin_verdict: Verdict | None = None
    cargo_verdict: Verdict | None = None
    #: 견종을 넣어 부른 경우에만 채워진다. 넣지 않으면 `None` 이고 견종 이야기는 안 나간다.
    breed_check: BreedCheck | None = None


def _verdict(
    allowed: bool | None,
    max_weight: Decimal | None,
    weight: Decimal | None,
    weight_unlimited: bool | None = None,
) -> Verdict | None:
    """가능 여부와 무게 상한으로 판정을 낸다.

    `weight` 가 없으면 판정하지 않는다(`None`). 사용자가 무게를 말하지 않았는데
    "가능합니다"라고 단정하면 안 되기 때문이다.

    `weight_unlimited` 가 `True` 면 "무게 제한 없음"이 명시된 것이라 무게 비교를
    생략하고 `ALLOWED` 다. 이게 없으면 상한 NULL 인 "무제한" 규정이 `WEIGHT_UNKNOWN`
    으로 떨어져 "무게 기준 미확인"으로 오답한다(플랜 2.3).
    """
    if weight is None:
        return None
    if allowed is None:
        return Verdict.UNKNOWN
    if allowed is False:
        return Verdict.NOT_ALLOWED
    if weight_unlimited is True:
        return Verdict.ALLOWED
    if max_weight is None:
        return Verdict.WEIGHT_UNKNOWN
    return Verdict.ALLOWED if weight <= max_weight else Verdict.OVER_WEIGHT


def _cargo_fee(rule: TransportPetRule, weight: Decimal | None) -> int | None:
    """위탁 요금은 무게 구간으로 갈린다.

    기준(`cargo_fee_threshold_kg`)을 넘으면 비싼 쪽이다. 무게를 모르면 요금도
    정하지 않는다 — 싼 쪽을 기본으로 두면 무거운 아이의 보호자가 실제보다 싸게 안다.
    """
    if weight is None or rule.cargo_fee_threshold_kg is None:
        return rule.cargo_fee_light_krw
    if weight > rule.cargo_fee_threshold_kg:
        return rule.cargo_fee_heavy_krw
    return rule.cargo_fee_light_krw


def search_guides(
    db: Session,
    *,
    category: GuideCategory | None = None,
    keywords: Sequence[str] | None = None,
    limit: int = DEFAULT_GUIDE_LIMIT,
) -> list[GuideHit]:
    """가이드 글을 찾는다.

    `keywords` 는 제목과 본문에서 **하나라도 걸리면**(OR) 통과다. AND 로 걸면
    "케이지 이름표"처럼 두 낱말을 붙여 물었을 때 0건이 되기 쉽다.
    """
    conditions = [GuideDocument.is_active.is_(True)]
    if category is not None:
        conditions.append(GuideDocument.category == category)

    matches = [
        or_(
            GuideDocument.title.ilike(f"%{keyword}%"),
            GuideDocument.body.ilike(f"%{keyword}%"),
        )
        for keyword in keywords or []
        if keyword.strip()
    ]
    if matches:
        conditions.append(or_(*matches))

    documents = db.scalars(
        select(GuideDocument)
        .where(*conditions)
        .order_by(GuideDocument.display_order, GuideDocument.title)
        .limit(min(limit, MAX_GUIDE_LIMIT))
    ).all()
    if not documents:
        return []

    sources = db.scalars(
        select(GuideDocumentSource)
        .where(GuideDocumentSource.guide_document_id.in_([d.id for d in documents]))
        .order_by(GuideDocumentSource.display_order)
    ).all()
    by_document: dict = {}
    for source in sources:
        by_document.setdefault(source.guide_document_id, []).append(
            (source.source_name, source.source_url)
        )

    return [
        GuideHit(
            slug=document.slug,
            title=document.title,
            category=document.category,
            body=document.body,
            sources=tuple(by_document.get(document.id, [])),
            verified_at=document.verified_at,
        )
        for document in documents
    ]


def _breed_checks(
    db: Session, rules: Sequence[TransportPetRule], breed_name: str
) -> dict[uuid.UUID, BreedCheck]:
    """회사마다 이 견종이 어디에 걸리는지 한 번에 대조한다.

    **걸린 항목이 없는 회사도 빠뜨리지 않는다.** 목록을 공개했는데 거기 없는 것과
    목록 자체가 없는 것을 구분해 돌려줘야 하고, 그러려면 회사마다 어떤 유형의
    목록을 갖고 있는지를 먼저 알아야 한다.
    """
    rule_ids = [rule.id for rule in rules]
    if not rule_ids:
        return {}

    rows = db.scalars(
        select(TransportRestrictedBreed).where(
            TransportRestrictedBreed.transport_pet_rule_id.in_(rule_ids)
        )
    ).all()

    matches: dict[uuid.UUID, list[BreedMatch]] = {}
    listed: dict[uuid.UUID, set[BreedRestrictionType]] = {}
    example_only: dict[uuid.UUID, set[BreedRestrictionType]] = {}
    for row in rows:
        bucket = example_only if row.is_example_only else listed
        bucket.setdefault(row.transport_pet_rule_id, set()).add(row.restriction_type)
        if breed_matches(breed_name, row.breed_name_ko):
            matches.setdefault(row.transport_pet_rule_id, []).append(
                BreedMatch(
                    breed_name_ko=row.breed_name_ko,
                    restriction_type=row.restriction_type,
                    applies_to=row.applies_to,
                    is_example_only=row.is_example_only,
                )
            )

    return {
        rule_id: BreedCheck(
            query=breed_name,
            matches=tuple(matches.get(rule_id, ())),
            listed_types=frozenset(listed.get(rule_id, ())),
            example_only_types=frozenset(example_only.get(rule_id, ())),
        )
        for rule_id in rule_ids
    }


def search_transport_rules(
    db: Session,
    *,
    carrier_type: CarrierType | None = None,
    carrier_name: str | None = None,
    pet_weight_kg: Decimal | None = None,
    breed_name: str | None = None,
) -> list[TransportRuleHit]:
    """운송사의 반려동물 규정을 찾는다.

    `carrier_name` 을 주면 그 회사만, 주지 않으면 종류 안의 전부를 돌려준다.
    비교하는 질문("어느 항공사가 되나요")이 많아 **전부 주는 쪽이 기본**이다.

    `pet_weight_kg` 를 주면 회사마다 판정이 붙는다. 판정은 여기서 계산한다 —
    숫자 비교를 모델에게 맡기지 않는다.

    `breed_name` 을 주면 회사별 제한 견종 목록과 대조한 결과(`breed_check`)가 붙는다.
    같은 이유다 — 견종 분류를 모델에게 맡기면 지어낸다.
    """
    conditions = []
    if carrier_type is not None:
        conditions.append(TransportPetRule.carrier_type == carrier_type)
    if carrier_name is not None and carrier_name.strip():
        conditions.append(TransportPetRule.carrier_name.ilike(f"%{carrier_name.strip()}%"))

    rules = db.scalars(
        select(TransportPetRule)
        .where(*conditions)
        .order_by(TransportPetRule.carrier_type, TransportPetRule.carrier_name)
        .limit(MAX_RULE_LIMIT)
    ).all()

    checks = _breed_checks(db, rules, breed_name) if breed_name and breed_name.strip() else {}

    return [
        TransportRuleHit(
            carrier_name=rule.carrier_name,
            carrier_type=rule.carrier_type,
            route=rule.route,
            cabin_allowed=rule.cabin_allowed,
            cabin_max_weight_kg=rule.cabin_max_weight_kg,
            cabin_weight_unlimited=rule.cabin_weight_unlimited,
            cabin_conditions=rule.cabin_conditions,
            cabin_fee_krw=rule.cabin_fee_krw,
            cargo_allowed=rule.cargo_allowed,
            cargo_max_weight_kg=rule.cargo_max_weight_kg,
            cargo_weight_unlimited=rule.cargo_weight_unlimited,
            cargo_fee_krw=_cargo_fee(rule, pet_weight_kg),
            same_day_request_allowed=rule.same_day_request_allowed,
            request_deadline_hours=rule.request_deadline_hours,
            pledge_required=rule.pledge_required,
            duration_minutes=rule.duration_minutes,
            notes=rule.notes,
            source_url=rule.source_url,
            verified_at=rule.verified_at,
            cabin_verdict=_verdict(
                rule.cabin_allowed,
                rule.cabin_max_weight_kg,
                pet_weight_kg,
                rule.cabin_weight_unlimited,
            ),
            cargo_verdict=_verdict(
                rule.cargo_allowed,
                rule.cargo_max_weight_kg,
                pet_weight_kg,
                rule.cargo_weight_unlimited,
            ),
            breed_check=checks.get(rule.id),
        )
        for rule in rules
    ]


__all__ = [
    "DEFAULT_GUIDE_LIMIT",
    "MAX_GUIDE_LIMIT",
    "BreedCheck",
    "BreedMatch",
    "GuideHit",
    "TransportRuleHit",
    "Verdict",
    "breed_matches",
    "search_guides",
    "search_transport_rules",
]
