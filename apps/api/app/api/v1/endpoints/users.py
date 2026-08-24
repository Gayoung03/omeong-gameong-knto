"""사용자 프로필 엔드포인트."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.db.models import Favorite, Route, TravelLog, User
from app.db.models.enums import RouteStatus
from app.db.session import get_db
from app.schemas.user import (
    ActivitySummary,
    NotificationPreferencesResponse,
    NotificationPreferencesUpdate,
    UserResponse,
    UserUpdate,
)

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


def _notification_preferences(user: User) -> NotificationPreferencesResponse:
    return NotificationPreferencesResponse(
        inquiry_answer_enabled=user.inquiry_answer_notification_enabled,
        marketing_enabled=user.marketing_notification_enabled,
    )


def _to_response(db: Session, user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        nickname=user.nickname,
        profile_image_url=user.profile_image_url,
        auth_provider=user.auth_provider,
        status="deleted" if user.deleted_at else "active",
        notification_preferences=_notification_preferences(user),
        activity_summary=ActivitySummary(
            saved_places_count=db.scalar(
                select(func.count()).select_from(Favorite).where(Favorite.user_id == user.id)
            )
            or 0,
            saved_routes_count=db.scalar(
                select(func.count())
                .select_from(Route)
                .where(Route.user_id == user.id, Route.status == RouteStatus.SAVED)
            )
            or 0,
            travel_logs_count=db.scalar(
                select(func.count()).select_from(TravelLog).where(TravelLog.user_id == user.id)
            )
            or 0,
        ),
        created_at=user.created_at,
    )


@router.get("/users/me", response_model=UserResponse, summary="내 정보 조회")
def get_me(current_user: CurrentUser, db: DbSession) -> UserResponse:
    return _to_response(db, current_user)


@router.patch("/users/me", response_model=UserResponse, summary="내 프로필 수정")
def update_me(payload: UserUpdate, current_user: CurrentUser, db: DbSession) -> UserResponse:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)
    return _to_response(db, current_user)


@router.patch(
    "/users/me/notification-preferences",
    response_model=NotificationPreferencesResponse,
    summary="알림 수신 설정 수정",
)
def update_notification_preferences(
    payload: NotificationPreferencesUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> NotificationPreferencesResponse:
    changes = payload.model_dump(exclude_unset=True)
    if "inquiry_answer_enabled" in changes:
        current_user.inquiry_answer_notification_enabled = changes["inquiry_answer_enabled"]
    if "marketing_enabled" in changes:
        current_user.marketing_notification_enabled = changes["marketing_enabled"]

    db.commit()
    db.refresh(current_user)
    return _notification_preferences(current_user)
