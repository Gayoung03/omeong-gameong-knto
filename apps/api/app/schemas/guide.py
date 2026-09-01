"""여행 가이드 API 스키마."""

import uuid
from datetime import datetime

from app.db.models.enums import CarrierType, GuideCategory
from app.schemas.base import APISchema


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
    cabin_fee_krw: int | None
    min_age_weeks_cabin: int | None
    max_pets_per_person_cabin: int | None
    max_pets_per_trip: int | None

    cargo_allowed: bool | None
    cargo_max_weight_kg: float | None
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


class TransportRuleListResponse(APISchema):
    items: list[TransportRuleResponse]
    total: int
    limit: int
    offset: int
