"""공지사항 조회 스키마."""

import uuid
from datetime import datetime

from app.schemas.base import APISchema


class NoticeListItem(APISchema):
    id: uuid.UUID
    title: str
    is_pinned: bool
    published_at: datetime


class NoticeDetail(NoticeListItem):
    content: str


class NoticeListResponse(APISchema):
    items: list[NoticeListItem]
    total: int
    limit: int
    offset: int
