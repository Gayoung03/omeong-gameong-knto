"""여행 가이드 API 스키마."""

import uuid
from datetime import datetime

from app.db.models.enums import (
    BreedRestrictionScope,
    BreedRestrictionType,
    CarrierType,
    GuideCategory,
)
from app.schemas.base import APISchema


class RestrictedBreedResponse(APISchema):
    breed_name_ko: str
    restriction_type: BreedRestrictionType
    applies_to: BreedRestrictionScope
    # true 면 원문이 예시만 든 것 — 앱은 확정 목록으로 표시하면 안 된다 (guides.md).
    is_example_only: bool


class GuideSourceResponse(APISchema):
    source_name: str
    source_url: str | None
    source_note: str | None
    verified_at: datetime | None


class GuideDocumentListItem(APISchema):
    id: uuid.UUID
    slug: str
    title: str
    category: GuideCategory
    summary: str
    verified_at: datetime | None
    sources: list[GuideSourceResponse]


class GuideDocumentDetail(GuideDocumentListItem):
    body: str


class GuideDocumentListResponse(APISchema):
    items: list[GuideDocumentListItem]
    total: int
    limit: int
    offset: int


class TransportRuleResponse(APISchema):
    id: uuid.UUID
    guide_document_id: uuid.UUID
    guide_slug: str
    guide_title: str
    category: GuideCategory
    carrier_name: str
    carrier_type: CarrierType
    route: str | None

    cabin_allowed: bool | None
    cabin_max_weight_kg: float | None
    # 무게 무제한 플래그 — true=상한 없음, false=상한 있음, null=미확인 (3값 유지).
    cabin_weight_unlimited: bool | None
    cabin_conditions: str | None
    cabin_fee_krw: int | None
    min_age_weeks_cabin: int | None
    max_pets_per_person_cabin: int | None
    max_pets_per_trip: int | None

    cargo_allowed: bool | None
    cargo_max_weight_kg: float | None
    cargo_weight_unlimited: bool | None
    cargo_fee_threshold_kg: float | None
    cargo_fee_light_krw: int | None
    cargo_fee_heavy_krw: int | None
    min_age_weeks_cargo: int | None

    pledge_required: bool | None
    online_checkin_allowed: bool | None
    same_day_request_allowed: bool | None
    request_deadline_hours: int | None
    airport_cage_price_krw: int | None
    duration_minutes: int | None

    notes: str | None
    source_url: str | None
    verified_at: datetime | None
    sources: list[GuideSourceResponse]
    restricted_breeds: list[RestrictedBreedResponse]


class TransportRuleListResponse(APISchema):
    items: list[TransportRuleResponse]
    total: int
    limit: int
    offset: int
