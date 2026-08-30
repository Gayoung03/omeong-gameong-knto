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
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.models.enums import CarrierType, GuideCategory
from app.db.models.guides import GuideDocument, GuideDocumentSource, TransportPetRule

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
    cabin_fee_krw: int | None
    cargo_allowed: bool | None
    cargo_max_weight_kg: Decimal | None
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


def _verdict(
    allowed: bool | None, max_weight: Decimal | None, weight: Decimal | None
) -> Verdict | None:
    """가능 여부와 무게 상한으로 판정을 낸다.

    `weight` 가 없으면 판정하지 않는다(`None`). 사용자가 무게를 말하지 않았는데
    "가능합니다"라고 단정하면 안 되기 때문이다.
    """
    if weight is None:
        return None
    if allowed is None:
        return Verdict.UNKNOWN
    if allowed is False:
        return Verdict.NOT_ALLOWED
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


def search_transport_rules(
    db: Session,
    *,
    carrier_type: CarrierType | None = None,
    carrier_name: str | None = None,
    pet_weight_kg: Decimal | None = None,
) -> list[TransportRuleHit]:
    """운송사의 반려동물 규정을 찾는다.

    `carrier_name` 을 주면 그 회사만, 주지 않으면 종류 안의 전부를 돌려준다.
    비교하는 질문("어느 항공사가 되나요")이 많아 **전부 주는 쪽이 기본**이다.

    `pet_weight_kg` 를 주면 회사마다 판정이 붙는다. 판정은 여기서 계산한다 —
    숫자 비교를 모델에게 맡기지 않는다.
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

    return [
        TransportRuleHit(
            carrier_name=rule.carrier_name,
            carrier_type=rule.carrier_type,
            route=rule.route,
            cabin_allowed=rule.cabin_allowed,
            cabin_max_weight_kg=rule.cabin_max_weight_kg,
            cabin_fee_krw=rule.cabin_fee_krw,
            cargo_allowed=rule.cargo_allowed,
            cargo_max_weight_kg=rule.cargo_max_weight_kg,
            cargo_fee_krw=_cargo_fee(rule, pet_weight_kg),
            same_day_request_allowed=rule.same_day_request_allowed,
            request_deadline_hours=rule.request_deadline_hours,
            pledge_required=rule.pledge_required,
            duration_minutes=rule.duration_minutes,
            notes=rule.notes,
            source_url=rule.source_url,
            verified_at=rule.verified_at,
            cabin_verdict=_verdict(rule.cabin_allowed, rule.cabin_max_weight_kg, pet_weight_kg),
            cargo_verdict=_verdict(rule.cargo_allowed, rule.cargo_max_weight_kg, pet_weight_kg),
        )
        for rule in rules
    ]


__all__ = [
    "DEFAULT_GUIDE_LIMIT",
    "MAX_GUIDE_LIMIT",
    "GuideHit",
    "TransportRuleHit",
    "Verdict",
    "search_guides",
    "search_transport_rules",
]
