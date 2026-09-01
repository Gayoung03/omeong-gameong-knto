"""Travel guide endpoints."""

import uuid
from collections import defaultdict
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.models import GuideDocument, GuideDocumentSource, TransportPetRule
from app.db.models.enums import CarrierType, GuideCategory
from app.db.session import get_db
from app.schemas.guide import (
    GuideDocumentDetail,
    GuideDocumentListItem,
    GuideDocumentListResponse,
    GuideSourceResponse,
    TransportRuleListResponse,
    TransportRuleResponse,
)

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]


def _summary(body: str, max_length: int = 92) -> str:
    """본문 첫 단락을 목록용 한 줄 요약으로 줄인다."""
    first_paragraph = next(
        (line.strip() for line in body.splitlines() if line.strip()),
        "",
    )
    if len(first_paragraph) <= max_length:
        return first_paragraph
    return f"{first_paragraph[: max_length - 1].rstrip()}…"


def _to_float(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None


def _sources_by_document(
    db: Session,
    document_ids: list[uuid.UUID],
) -> dict[uuid.UUID, list[GuideSourceResponse]]:
    if not document_ids:
        return {}

    sources = db.scalars(
        select(GuideDocumentSource)
        .where(GuideDocumentSource.guide_document_id.in_(document_ids))
        .order_by(GuideDocumentSource.display_order, GuideDocumentSource.source_name)
    ).all()

    result: dict[uuid.UUID, list[GuideSourceResponse]] = defaultdict(list)
    for source in sources:
        result[source.guide_document_id].append(
            GuideSourceResponse(
                source_name=source.source_name,
                source_url=source.source_url,
                source_note=source.source_note,
                verified_at=source.verified_at,
            )
        )
    return result


def _document_list_item(
    document: GuideDocument,
    sources: list[GuideSourceResponse],
) -> GuideDocumentListItem:
    return GuideDocumentListItem(
        id=document.id,
        slug=document.slug,
        title=document.title,
        category=document.category,
        summary=_summary(document.body),
        verified_at=document.verified_at,
        sources=sources,
    )


def _transport_rule_response(
    rule: TransportPetRule,
    document: GuideDocument,
    sources: list[GuideSourceResponse],
) -> TransportRuleResponse:
    return TransportRuleResponse(
        id=rule.id,
        guide_document_id=document.id,
        guide_slug=document.slug,
        guide_title=document.title,
        category=document.category,
        carrier_name=rule.carrier_name,
        carrier_type=rule.carrier_type,
        route=rule.route,
        cabin_allowed=rule.cabin_allowed,
        cabin_max_weight_kg=_to_float(rule.cabin_max_weight_kg),
        cabin_fee_krw=rule.cabin_fee_krw,
        min_age_weeks_cabin=rule.min_age_weeks_cabin,
        max_pets_per_person_cabin=rule.max_pets_per_person_cabin,
        max_pets_per_trip=rule.max_pets_per_trip,
        cargo_allowed=rule.cargo_allowed,
        cargo_max_weight_kg=_to_float(rule.cargo_max_weight_kg),
        cargo_fee_threshold_kg=_to_float(rule.cargo_fee_threshold_kg),
        cargo_fee_light_krw=rule.cargo_fee_light_krw,
        cargo_fee_heavy_krw=rule.cargo_fee_heavy_krw,
        min_age_weeks_cargo=rule.min_age_weeks_cargo,
        pledge_required=rule.pledge_required,
        online_checkin_allowed=rule.online_checkin_allowed,
        same_day_request_allowed=rule.same_day_request_allowed,
        request_deadline_hours=rule.request_deadline_hours,
        airport_cage_price_krw=rule.airport_cage_price_krw,
        duration_minutes=rule.duration_minutes,
        notes=rule.notes,
        source_url=rule.source_url,
        verified_at=rule.verified_at,
        sources=sources,
    )


@router.get("/guides", response_model=GuideDocumentListResponse, summary="여행 가이드 문서 목록")
def list_guides(
    db: DbSession,
    category: GuideCategory | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> GuideDocumentListResponse:
    conditions = [GuideDocument.is_active.is_(True)]
    if category:
        conditions.append(GuideDocument.category == category)

    total = db.scalar(select(func.count(GuideDocument.id)).where(*conditions)) or 0
    documents = db.scalars(
        select(GuideDocument)
        .where(*conditions)
        .order_by(GuideDocument.display_order, GuideDocument.title)
        .limit(limit)
        .offset(offset)
    ).all()
    source_map = _sources_by_document(db, [document.id for document in documents])

    return GuideDocumentListResponse(
        items=[
            _document_list_item(document, source_map.get(document.id, []))
            for document in documents
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/guides/transport-rules",
    response_model=TransportRuleListResponse,
    summary="반려동물 운송 규정 목록",
)
def list_transport_rules(
    db: DbSession,
    carrier_type: Annotated[CarrierType | None, Query(alias="carrierType")] = None,
    q: Annotated[str | None, Query(description="운송사명 또는 항로 검색어")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TransportRuleListResponse:
    conditions = [GuideDocument.is_active.is_(True)]
    if carrier_type:
        conditions.append(TransportPetRule.carrier_type == carrier_type)
    if q:
        keyword = f"%{q}%"
        conditions.append(
            or_(
                TransportPetRule.carrier_name.ilike(keyword),
                TransportPetRule.route.ilike(keyword),
                GuideDocument.title.ilike(keyword),
            )
        )

    total = (
        db.scalar(
            select(func.count(TransportPetRule.id))
            .join(GuideDocument, TransportPetRule.guide_document_id == GuideDocument.id)
            .where(*conditions)
        )
        or 0
    )
    rows = db.execute(
        select(TransportPetRule, GuideDocument)
        .join(GuideDocument, TransportPetRule.guide_document_id == GuideDocument.id)
        .where(*conditions)
        .order_by(
            TransportPetRule.carrier_type,
            GuideDocument.display_order,
            TransportPetRule.route,
            TransportPetRule.carrier_name,
        )
        .limit(limit)
        .offset(offset)
    ).all()
    source_map = _sources_by_document(db, [row[1].id for row in rows])

    return TransportRuleListResponse(
        items=[
            _transport_rule_response(rule, document, source_map.get(document.id, []))
            for rule, document in rows
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/guides/transport-rules/{rule_id}",
    response_model=TransportRuleResponse,
    summary="반려동물 운송 규정 상세",
)
def get_transport_rule(rule_id: uuid.UUID, db: DbSession) -> TransportRuleResponse:
    row = db.execute(
        select(TransportPetRule, GuideDocument)
        .join(GuideDocument, TransportPetRule.guide_document_id == GuideDocument.id)
        .where(TransportPetRule.id == rule_id, GuideDocument.is_active.is_(True))
    ).one_or_none()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="가이드를 찾을 수 없습니다",
        )

    rule, document = row
    source_map = _sources_by_document(db, [document.id])
    return _transport_rule_response(rule, document, source_map.get(document.id, []))


@router.get(
    "/guides/{guide_slug}",
    response_model=GuideDocumentDetail,
    summary="여행 가이드 문서 상세",
)
def get_guide(guide_slug: str, db: DbSession) -> GuideDocumentDetail:
    document = db.scalar(
        select(GuideDocument).where(
            GuideDocument.slug == guide_slug,
            GuideDocument.is_active.is_(True),
        )
    )
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="가이드를 찾을 수 없습니다",
        )

    source_map = _sources_by_document(db, [document.id])
    return GuideDocumentDetail(
        **_document_list_item(document, source_map.get(document.id, [])).model_dump(),
        body=document.body,
    )
