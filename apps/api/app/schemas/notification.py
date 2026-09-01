"""알림함과 푸시 토큰 API 스키마."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas.base import APISchema


class NotificationItem(APISchema):
    id: uuid.UUID
    type: str
    target_id: uuid.UUID | None
    title: str
    content: str
    is_read: bool
    created_at: datetime
    read_at: datetime | None


class NotificationListResponse(APISchema):
    items: list[NotificationItem]
    total: int
    limit: int
    offset: int


class UnreadCountResponse(APISchema):
    count: int


class PushTokenCreate(APISchema):
    token: str = Field(min_length=10, max_length=255)
    platform: Literal["ios", "android"]


class PushTokenDelete(APISchema):
    token: str = Field(min_length=10, max_length=255)


class WebPushPublicKeyResponse(APISchema):
    public_key: str


class WebPushSubscriptionCreate(APISchema):
    endpoint: str = Field(min_length=10, max_length=2048)
    p256dh: str = Field(min_length=10, max_length=512)
    auth: str = Field(min_length=5, max_length=512)


class WebPushSubscriptionDelete(APISchema):
    endpoint: str = Field(min_length=10, max_length=2048)
