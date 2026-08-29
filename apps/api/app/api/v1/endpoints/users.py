"""사용자 프로필 엔드포인트."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.core.security import verify_password
from app.db.models import Favorite, Route, TravelLog, User, UserTravelPreference
from app.db.models.enums import AuthProvider, RouteStatus
from app.db.session import get_db
from app.schemas.travel_preference import TravelPreferenceResponse, TravelPreferenceUpsert
from app.schemas.user import (
    AccountDeleteRequest,
    ActivitySummary,
    NotificationPreferencesResponse,
    NotificationPreferencesUpdate,
    UserResponse,
    UserUpdate,
)
from app.services.travel_preferences import upsert_travel_preference

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


@router.delete("/users/me", status_code=status.HTTP_204_NO_CONTENT, summary="회원 탈퇴")
def delete_me(
    payload: AccountDeleteRequest, current_user: CurrentUser, db: DbSession
) -> Response:
    """물리 삭제가 아니라 `deleted_at` 을 기록해 soft delete 한다(users.md).

    local 계정은 비밀번호로 재확인한다. **소셜 계정의 `providerAccessToken` 재인증
    분기는 Phase 5** — 지금은 signup 이 local 계정만 만들어 소셜 계정이 존재하지 않는다.
    이메일·닉네임 익명화는 탈퇴 30일 뒤 배치가 담당하므로 여기서 하지 않는다.

    탈퇴 후 이 사용자의 토큰이 401 이 되는 것은 Phase 4(`get_current_user` 가 토큰을
    실제 검증하고 `deleted_at` 을 보게 될 때) 완성된다.
    """
    if current_user.auth_provider == AuthProvider.LOCAL:
        password = payload.password.get_secret_value() if payload.password else ""
        if current_user.password_hash is None or not verify_password(
            password, current_user.password_hash
        ):
            raise HTTPException(status_code=401, detail="비밀번호가 일치하지 않습니다")
    else:
        # Phase 5 전까지 소셜 계정은 생성되지 않아 도달 불가한 방어 분기.
        raise HTTPException(status_code=401, detail="재인증이 필요합니다")

    current_user.deleted_at = datetime.now(UTC)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/users/me/travel-preference",
    response_model=TravelPreferenceResponse,
    summary="기본 여행 취향 조회",
)
def get_travel_preference(
    current_user: CurrentUser, db: DbSession
) -> TravelPreferenceResponse:
    preference = db.get(UserTravelPreference, current_user.id)
    if preference is None:
        # 취향을 한 번도 저장하지 않은 사용자. 명세는 행 존재를 전제하지만 빈 상태를
        # 명시하지 않아, 항상 200 + 기본값 모양(companionCount=1)을 돌려준다.
        return TravelPreferenceResponse(
            default_pace=None,
            default_transport=None,
            departure_location=None,
            preferred_duration_days=None,
            companion_count=1,
            preferred_tags=None,
            updated_at=None,
        )
    return TravelPreferenceResponse.model_validate(preference)


@router.put(
    "/users/me/travel-preference",
    response_model=TravelPreferenceResponse,
    summary="기본 여행 취향 수정",
)
def put_travel_preference(
    payload: TravelPreferenceUpsert, current_user: CurrentUser, db: DbSession
) -> TravelPreferenceResponse:
    """전체 덮어쓰기(PUT). 보내지 않은 필드도 기본값으로 채워 전부 설정한다.

    upsert 서비스가 없으면 만들고 있으면 갱신한다(가입과 같은 규칙 재사용).
    """
    preference = upsert_travel_preference(db, current_user.id, payload.model_dump())
    db.commit()
    db.refresh(preference)
    return TravelPreferenceResponse.model_validate(preference)


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
