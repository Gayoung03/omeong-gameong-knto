"""1:1 문의 API 스키마 (사용자용).

카테고리는 **영문 코드**로 통일한다(docs/api/notifications.md · README 7장 규약).
화면에 보일 한글 라벨은 앱과 관리자 콘솔이 각자 라벨 맵으로 바꾼다.

문의는 작성 후 **수정·삭제할 수 없다** — 답변이 달린 뒤 내용이 바뀌면 대화가
어긋나기 때문이다. 그래서 Update 스키마가 없다.
"""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator

from app.schemas.base import APISchema
from app.schemas.validators import ImageUrl

#: 서버가 이 6개 값만 넣는다는 약속(docs/api/notifications.md, 2026-08-18 확정).
InquiryCategory = Literal["account", "pet", "saved", "schedule", "bug", "etc"]

#: DB CHECK `status_valid` 와 같은 값.
InquiryStatus = Literal["pending", "completed"]

#: 첨부 이미지 최대 개수. 별도 테이블 없이 배열 컬럼에 담는다.
MAX_INQUIRY_IMAGES = 5


class InquiryListItem(APISchema):
    """목록 항목. `content`·`answer`·`imageUrls` 는 상세에서만 내려준다."""

    id: uuid.UUID
    category: InquiryCategory
    status: InquiryStatus
    title: str
    created_at: datetime
    answered_at: datetime | None


class InquiryDetail(InquiryListItem):
    content: str
    #: DB 컬럼은 nullable ARRAY 라 None 일 수 있다. 응답은 항상 배열로 통일한다.
    image_urls: list[str] = Field(default_factory=list)
    answer: str | None
    updated_at: datetime

    @field_validator("image_urls", mode="before")
    @classmethod
    def _none_to_empty(cls, value: object) -> object:
        return value if value is not None else []


class InquiryListResponse(APISchema):
    items: list[InquiryListItem]
    total: int
    limit: int
    offset: int


class InquiryCreate(APISchema):
    category: InquiryCategory
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)
    #: `POST /uploads` 로 먼저 받은 우리 저장소 주소만 허용한다.
    image_urls: list[ImageUrl] = Field(
        default_factory=list, max_length=MAX_INQUIRY_IMAGES
    )
