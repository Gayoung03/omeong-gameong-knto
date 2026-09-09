"""route_items·route_item_candidates 저장 helpers.

`route_recommendation._save_itinerary`(그대로 orchestrator 에 남음)와 편집 경로가
쓴다. 이 모듈은 상위 orchestrator 를 import 하지 않는다(단방향).
"""

import uuid
from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.models import RouteItem, RouteItemCandidate
from app.db.models.enums import RouteItemSlotStatus
from app.recommend.config.pet_policy_reason import NEEDS_CHECK_REASON
from app.recommend.itinerary import MAX_ALTERNATIVES, RouteAnchor
from app.recommend.schemas import CandidateTier, ScoredCandidate


def _slot_status_of(tier: CandidateTier) -> RouteItemSlotStatus:
    return (
        RouteItemSlotStatus.NEEDS_VERIFICATION
        if tier == CandidateTier.NEEDS_CHECK
        else RouteItemSlotStatus.FILLED
    )


def _save_alternatives(
    db: Session, route_item_id: uuid.UUID, candidates: tuple[ScoredCandidate, ...]
) -> None:
    """채워진 항목의 "대신 갈 곳" 대안. 실제 점수·근거를 그대로 담는다."""
    for rank, candidate in enumerate(candidates[:MAX_ALTERNATIVES], start=1):
        db.add(
            RouteItemCandidate(
                route_item_id=route_item_id,
                place_id=candidate.place_id,
                rank=rank,
                recommendation_score=Decimal(str(round(candidate.total_score * 100, 2))),
                recommendation_reason=candidate.reason,
                requires_verification=candidate.tier == CandidateTier.NEEDS_CHECK,
            )
        )


def _save_unfilled_candidates(
    db: Session, route_item_id: uuid.UUID, candidates: tuple[ScoredCandidate, ...]
) -> None:
    """빈 슬롯의 "확인 필요 후보". 전화번호는 응답의 phone 필드로 내리고 근거엔 안내만."""
    for rank, candidate in enumerate(candidates[:MAX_ALTERNATIVES], start=1):
        db.add(
            RouteItemCandidate(
                route_item_id=route_item_id,
                place_id=candidate.place_id,
                rank=rank,
                recommendation_score=None,
                recommendation_reason=NEEDS_CHECK_REASON,
                requires_verification=True,
            )
        )


def _save_anchor(
    db: Session,
    route_day_id: uuid.UUID,
    anchor: RouteAnchor,
    sort_order: int,
    starts_at,
) -> uuid.UUID:
    item = RouteItem(
        route_day_id=route_day_id,
        place_id=anchor.place_id,
        custom_place_name=None if anchor.place_id else anchor.name,
        custom_address=anchor.address,
        latitude=Decimal(str(anchor.coord[0])),
        longitude=Decimal(str(anchor.coord[1])),
        item_type=anchor.item_type,
        sort_order=sort_order,
        starts_at=starts_at,
        stay_minutes=0,
    )
    db.add(item)
    db.flush()
    return item.id
