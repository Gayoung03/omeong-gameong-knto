"""관리자용 1:1 문의 API 스키마."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator

from app.schemas.base import APISchema
from app.schemas.inquiry import InquiryCategory, InquiryStatus

AdminInquirySort = Literal["created_at", "answered_at"]
AdminInquiryOrder = Literal["asc", "desc"]


class AdminInquiryAsker(APISchema):
    id: uuid.UUID
    nickname: str
    email: str | None


class AdminInquiryAuditResponse(APISchema):
    id: uuid.UUID
    actor_user_id: uuid.UUID
    action: str
    previous_status: str | None
    next_status: str | None
    changes: dict
    created_at: datetime


class AdminInquiryListItem(APISchema):
    id: uuid.UUID
    category: InquiryCategory
    status: InquiryStatus
    title: str
    asker_nickname: str
    created_at: datetime
    answered_at: datetime | None


class AdminInquiryListResponse(APISchema):
    items: list[AdminInquiryListItem]
    total: int
    page: int
    limit: int


class AdminInquiryDetail(APISchema):
    id: uuid.UUID
    category: InquiryCategory
    status: InquiryStatus
    title: str
    content: str
    image_urls: list[str] = Field(default_factory=list)
    #: 완료된 문의는 관리자가 보낸 전체 답변이 담긴다.
    answer: str | None
    answered_at: datetime | None
    #: 답변 편집기 초기값(머릿말 + 빈 본문 + 꼬릿말). 관리자가 자유롭게 수정한다.
    answer_template: str
    asker: AdminInquiryAsker
    created_at: datetime
    updated_at: datetime
    audit_logs: list[AdminInquiryAuditResponse]

    @field_validator("image_urls", mode="before")
    @classmethod
    def _none_to_empty(cls, value: object) -> object:
        return value if value is not None else []


class AdminInquiryAnswerRequest(APISchema):
    #: 문의자에게 전달될 답변 전체(머릿말·꼬릿말 포함). 보낸 그대로 저장된다.
    answer: str = Field(min_length=1, max_length=8000)

    @field_validator("answer")
    @classmethod
    def _strip_non_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("답변 내용을 입력해 주세요")
        return value


class AdminInquiryDraftResponse(APISchema):
    reply: str
    used_context: list[str]
    needs_human_review: bool
    model: str
