"""관리자용 여행 이야기 검수 API 스키마."""

import uuid
from datetime import datetime
from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import AwareDatetime, Field, field_validator, model_validator

from app.db.models.enums import EditorialStoryKind, EditorialStoryStatus
from app.schemas.base import APISchema


class AdminUserResponse(APISchema):
    id: uuid.UUID
    email: str | None
    nickname: str
    is_admin: bool


class AdminEditorialSection(APISchema):
    id: str = Field(min_length=1, max_length=100)
    heading: str = Field(min_length=1, max_length=200)
    paragraphs: list[str] = Field(min_length=1)
    image_url: str | None = None
    image_caption: str | None = Field(default=None, max_length=300)

    @field_validator("paragraphs")
    @classmethod
    def validate_paragraphs(cls, paragraphs: list[str]) -> list[str]:
        if any(not paragraph.strip() for paragraph in paragraphs):
            raise ValueError("본문 문단은 비어 있을 수 없습니다")
        return paragraphs

    @field_validator("image_url")
    @classmethod
    def validate_optional_image_url(cls, value: str | None) -> str | None:
        if value is None:
            return value
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("이미지는 http(s) 절대 URL이어야 합니다")
        return value


class AdminEditorialSourceResponse(APISchema):
    id: uuid.UUID
    provider: str
    external_id: str
    source_name: str
    source_title: str
    source_url: str
    source_image_url: str | None
    source_published_at: datetime | None
    collected_at: datetime


class AdminEditorialAuditResponse(APISchema):
    id: uuid.UUID
    actor_user_id: uuid.UUID
    action: str
    previous_status: str | None
    next_status: str | None
    changes: dict
    created_at: datetime


class AdminEditorialStoryListItem(APISchema):
    id: uuid.UUID
    slug: str
    kind: EditorialStoryKind
    category: str
    card_title: str
    title: str
    status: EditorialStoryStatus
    source_names: list[str]
    collected_at: datetime | None
    published_at: datetime | None
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AdminEditorialStoryListResponse(APISchema):
    items: list[AdminEditorialStoryListItem]
    total: int
    page: int
    limit: int


class AdminEditorialStoryDetail(APISchema):
    id: uuid.UUID
    slug: str
    kind: EditorialStoryKind
    category: str
    card_title: str
    title: str
    summary: str
    hero_image_url: str
    sections: list[AdminEditorialSection]
    tips: list[str]
    tags: list[str]
    status: EditorialStoryStatus
    display_order: int
    generated_by_ai: bool
    generation_model: str | None
    published_at: datetime | None
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime
    sources: list[AdminEditorialSourceResponse]
    audit_logs: list[AdminEditorialAuditResponse]


class AdminEditorialStoryUpdate(APISchema):
    kind: EditorialStoryKind | None = None
    category: str | None = Field(default=None, min_length=1, max_length=50)
    card_title: str | None = Field(default=None, min_length=1, max_length=160)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    summary: str | None = Field(default=None, min_length=1)
    hero_image_url: str | None = Field(default=None, min_length=1)
    sections: list[AdminEditorialSection] | None = Field(default=None, min_length=1)
    tips: list[str] | None = None
    tags: list[str] | None = None
    display_order: int | None = Field(default=None, ge=-32768, le=32767)
    published_at: AwareDatetime | None = None
    expires_at: AwareDatetime | None = None

    @field_validator("category", "card_title", "title", "summary", "hero_image_url")
    @classmethod
    def strip_required_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("빈 문자열은 저장할 수 없습니다")
        return value

    @field_validator("tips", "tags")
    @classmethod
    def strip_string_list(cls, values: list[str] | None) -> list[str] | None:
        if values is None:
            return values
        cleaned = [value.strip() for value in values]
        if any(not value for value in cleaned):
            raise ValueError("빈 항목은 저장할 수 없습니다")
        return cleaned

    @field_validator("hero_image_url")
    @classmethod
    def validate_hero_image_url(cls, value: str | None) -> str | None:
        if value is None:
            return value
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("대표 이미지는 http(s) 절대 URL이어야 합니다")
        return value

    @model_validator(mode="after")
    def validate_patch_values(self) -> Self:
        required_fields = {
            "kind",
            "category",
            "card_title",
            "title",
            "summary",
            "hero_image_url",
            "sections",
            "tips",
            "tags",
            "display_order",
        }
        if any(
            field in self.model_fields_set and getattr(self, field) is None
            for field in required_fields
        ):
            raise ValueError("필수 필드는 null로 저장할 수 없습니다")
        if self.tags is not None and any(len(tag) > 50 for tag in self.tags):
            raise ValueError("태그는 50자 이하로 입력해 주세요")
        if self.sections is not None:
            section_ids = [section.id for section in self.sections]
            if len(section_ids) != len(set(section_ids)):
                raise ValueError("본문 섹션 id는 중복될 수 없습니다")
        return self


class AdminEditorialPublishRequest(APISchema):
    published_at: AwareDatetime | None = None


AdminEditorialSort = Literal["collected_at", "published_at"]
AdminEditorialOrder = Literal["asc", "desc"]
