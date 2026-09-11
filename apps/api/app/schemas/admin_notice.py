"""관리자용 공지사항 API 스키마."""

import uuid
from datetime import datetime
from typing import Literal, Self

from pydantic import AwareDatetime, Field, field_validator, model_validator

from app.schemas.base import APISchema

#: 관리자 목록 탭. announced = 발송 완료, draft = 아직 발송 전.
AdminNoticeFilter = Literal["all", "announced", "draft"]


class AdminNoticeAuditResponse(APISchema):
    id: uuid.UUID
    actor_user_id: uuid.UUID
    action: str
    previous_status: str | None
    next_status: str | None
    changes: dict
    created_at: datetime


class AdminNoticeListItem(APISchema):
    id: uuid.UUID
    title: str
    is_pinned: bool
    is_active: bool
    published_at: datetime
    announced_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AdminNoticeListResponse(APISchema):
    items: list[AdminNoticeListItem]
    total: int
    page: int
    limit: int


class AdminNoticeDetail(AdminNoticeListItem):
    content: str
    audit_logs: list[AdminNoticeAuditResponse]


class AdminNoticeCreate(APISchema):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)
    is_pinned: bool = False
    #: 비우면 서버가 now() 로 채운다(초안은 is_active=false 라 어차피 숨겨짐).
    published_at: AwareDatetime | None = None

    @field_validator("title", "content")
    @classmethod
    def _strip_required(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("빈 값은 저장할 수 없습니다")
        return value


class AdminNoticeUpdate(APISchema):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = Field(default=None, min_length=1)
    is_pinned: bool | None = None
    is_active: bool | None = None
    published_at: AwareDatetime | None = None

    @field_validator("title", "content")
    @classmethod
    def _strip_required(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("빈 문자열은 저장할 수 없습니다")
        return value

    @model_validator(mode="after")
    def _no_null_required(self) -> Self:
        for name in ("title", "content", "is_pinned", "is_active", "published_at"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError("필수 필드는 null로 저장할 수 없습니다")
        return self


class AdminNoticePublishRequest(APISchema):
    published_at: AwareDatetime | None = None
