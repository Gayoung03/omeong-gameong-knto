"""사용자 프로필 API 스키마."""

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, StringConstraints, field_validator

from app.db.models.enums import AuthProvider
from app.schemas.base import APISchema

Nickname = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]


class NotificationPreferencesResponse(APISchema):
    inquiry_answer_enabled: bool
    marketing_enabled: bool


class NotificationPreferencesUpdate(APISchema):
    inquiry_answer_enabled: bool | None = None
    marketing_enabled: bool | None = None

    @field_validator("inquiry_answer_enabled", "marketing_enabled")
    @classmethod
    def reject_null(cls, value: bool | None) -> bool:
        if value is None:
            raise ValueError("알림 설정은 null일 수 없습니다")
        return value


class ActivitySummary(APISchema):
    saved_places_count: int
    saved_routes_count: int
    travel_logs_count: int


class UserResponse(APISchema):
    id: uuid.UUID
    email: str | None
    nickname: str
    profile_image_url: str | None
    auth_provider: AuthProvider
    status: Literal["active", "deleted"]
    notification_preferences: NotificationPreferencesResponse
    activity_summary: ActivitySummary
    created_at: datetime


class UserUpdate(APISchema):
    nickname: Nickname | None = None
    profile_image_url: str | None = Field(default=None)

    @field_validator("nickname")
    @classmethod
    def reject_null_nickname(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("nickname은 null일 수 없습니다")
        return value
