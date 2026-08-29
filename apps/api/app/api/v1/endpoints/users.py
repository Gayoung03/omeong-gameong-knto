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
from app.integrations.social_auth.kakao import (
    KakaoOAuthClient,
    SocialAuthError,
    SocialProviderUnavailable,
    get_kakao_client,
)
from app.schemas.travel_preference import TravelPreferenceResponse, TravelPreferenceUpsert
from app.schemas.user import (
    AccountDeleteRequest,
    ActivitySummary,
    NotificationPreferencesResponse,
    NotificationPreferencesUpdate,
    UserResponse,
    UserUpdate,
)
from app.services.social_auth import find_social_account
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
    payload: AccountDeleteRequest,
    current_user: CurrentUser,
    db: DbSession,
    kakao: Annotated[KakaoOAuthClient, Depends(get_kakao_client)],
) -> Response:
    """물리 삭제가 아니라 `deleted_at` 을 기록해 soft delete 한다(users.md).

    local 계정은 비밀번호로 재확인한다. 소셜 계정은 비밀번호가 없어, 앱이 제공처
    재인증으로 얻은 `providerAccessToken` 을 검증하고 그 토큰이 이 회원의 소셜 계정
    소유인지 확인한다. 이메일·닉네임 익명화는 탈퇴 30일 뒤 배치가 담당한다.
    """
    if current_user.auth_provider == AuthProvider.LOCAL:
        password = payload.password.get_secret_value() if payload.password else ""
        if current_user.password_hash is None or not verify_password(
            password, current_user.password_hash
        ):
            raise HTTPException(status_code=401, detail="비밀번호가 일치하지 않습니다")
    else:
        _reauthenticate_social(db, kakao, current_user, payload.provider_access_token)

    current_user.deleted_at = datetime.now(UTC)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _reauthenticate_social(
    db: Session, kakao: KakaoOAuthClient, user: User, provider_access_token: str | None
) -> None:
    """소셜 계정 탈퇴 재인증. 제공처 토큰이 유효하고 **이 회원 소유**인지 확인한다."""
    if not provider_access_token:
        raise HTTPException(status_code=401, detail="재인증이 필요합니다")
    try:
        profile = kakao.verify_access_token(provider_access_token)
    except SocialAuthError:
        raise HTTPException(status_code=401, detail="재인증이 필요합니다") from None
    except SocialProviderUnavailable:
        raise HTTPException(
            status_code=502, detail="소셜 제공처가 응답하지 않습니다"
        ) from None

    account = find_social_account(db, profile.provider, profile.provider_user_id)
    # 유효한 토큰이라도 다른 회원의 계정이면 거부한다(남의 토큰으로 탈퇴 방지).
    if account is None or account.user_id != user.id:
        raise HTTPException(status_code=401, detail="재인증이 필요합니다")


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
