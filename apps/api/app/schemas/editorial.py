"""제주 여행 이야기 공개 API 스키마."""

import uuid
from datetime import datetime

from app.db.models.enums import EditorialStoryKind
from app.schemas.base import APISchema


class EditorialSection(APISchema):
    id: str
    heading: str
    paragraphs: list[str]
    image_url: str | None = None
    image_caption: str | None = None


class EditorialSourceResponse(APISchema):
    source_name: str
    source_title: str
    source_url: str
    source_published_at: datetime | None


class EditorialStoryResponse(APISchema):
    id: uuid.UUID
    slug: str
    kind: EditorialStoryKind
    category: str
    card_title: str
    title: str
    summary: str
    hero_image_url: str
    published_at: datetime
    reading_minutes: int
    author: str = "오멍가멍 에디터"
    sections: list[EditorialSection]
    tips: list[str]
    tags: list[str]
    sources: list[EditorialSourceResponse]


class EditorialStoryListResponse(APISchema):
    items: list[EditorialStoryResponse]
    total: int
