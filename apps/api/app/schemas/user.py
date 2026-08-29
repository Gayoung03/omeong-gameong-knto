"""사용자 프로필 API 스키마."""

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, SecretStr, StringConstraints, field_validator

from app.db.models.enums import AuthProvider
from app.schemas.base import APISchema
from app.schemas.validators import OptionalImageUrl

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
    profile_image_url: OptionalImageUrl = Field(default=None)

    @field_validator("nickname")
    @classmethod
    def reject_null_nickname(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("nickname은 null일 수 없습니다")
        return value


class AccountDeleteRequest(APISchema):
    """회원 탈퇴 요청.

    `local` 계정은 `password` 로 재확인한다. 소셜 계정은 `providerAccessToken` 재인증
    이지만 그 분기는 Phase 5 — 지금은 signup 이 local 계정만 만들어 소셜 계정이 없다.
    """

    password: SecretStr | None = None
