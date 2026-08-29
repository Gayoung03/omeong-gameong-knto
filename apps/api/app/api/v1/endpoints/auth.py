"""이메일 인증 엔드포인트 (docs/api/auth.md 확정 명세).

이 단계(Phase 3)는 **토큰을 발급만** 한다. 발급된 access token 을 실제로 검증해
사용자를 식별하는 전환(`get_current_user` 교체)은 Phase 4 다 — 프론트 영향을
격리하려고 분리했다. 그래서 `logout` 은 아직 개발용 고정 사용자(스텁)를 받는다.

소셜 로그인(kakao·google)은 Phase 5 다. 여기엔 이메일 경로만 있다.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import (
    ACCESS_TOKEN_EXPIRES_IN,
    DUMMY_PASSWORD_HASH,
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.models import User
from app.db.models.enums import AuthProvider
from app.db.session import get_db
from app.schemas.auth import (
    AuthUser,
    LoginRequest,
    RefreshRequest,
    RefreshTokenResponse,
    SignupRequest,
    TokenResponse,
)
from app.services import pets as pet_service
from app.services.travel_preferences import upsert_travel_preference

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]

#: 이메일 없음·비번 불일치·탈퇴를 구분하지 않는 로그인 실패 메시지(가입 이메일
#: 목록이 새지 않도록 같은 401 로 통일).
_LOGIN_FAILED = "이메일 또는 비밀번호가 올바르지 않습니다"
_TOKEN_INVALID = "토큰이 유효하지 않습니다"


def _auth_user(user: User) -> AuthUser:
    return AuthUser(
        id=user.id,
        email=user.email,
        nickname=user.nickname,
        profile_image_url=user.profile_image_url,
        auth_provider=user.auth_provider,
        status="deleted" if user.deleted_at else "active",
    )


def _issue_tokens(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        expires_in=ACCESS_TOKEN_EXPIRES_IN,
        user=_auth_user(user),
    )


@router.post(
    "/auth/signup", response_model=TokenResponse, status_code=201, summary="이메일 회원가입"
)
def signup(payload: SignupRequest, db: DbSession) -> TokenResponse:
    """계정·반려동물·여행취향을 **한 트랜잭션**으로 저장하고 바로 로그인 상태로 만든다."""
    # 흔한 중복은 명시적 409 로(탈퇴 계정 이메일도 soft delete 라 행이 남아 포함).
    # 동시 요청 경합은 users.email UNIQUE + 전역 IntegrityError 핸들러가 409 로 받는다.
    if db.scalar(select(User.id).where(User.email == payload.email)) is not None:
        raise HTTPException(status_code=409, detail="이미 가입된 이메일입니다")

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password.get_secret_value()),
        nickname=payload.nickname,
        # authProvider 는 서버가 정한다 — 클라이언트가 보내지 않는다.
        auth_provider=AuthProvider.LOCAL,
    )
    db.add(user)
    db.flush()

    if payload.pet is not None:
        # 첫 펫 자동 대표 규칙은 Phase 2 서비스가 갖는다(commit 은 아래 한 번).
        pet_service.create_pet(db, user.id, payload.pet)

    # 취향을 건너뛰어도 기본값 행을 만든다 — GET 이 항상 같은 모양을 돌려주도록.
    values = payload.travel_preference.model_dump() if payload.travel_preference else {}
    upsert_travel_preference(db, user.id, values)

    db.commit()
    db.refresh(user)
    return _issue_tokens(user)


@router.post("/auth/login", response_model=TokenResponse, summary="이메일 로그인")
def login(payload: LoginRequest, db: DbSession) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email))
    password = payload.password.get_secret_value()

    # 이메일이 없어도(=user None) 더미 해시로 검증 비용을 동일하게 치른다 —
    # 응답 시간 차로 "가입된 이메일"을 알아내지 못하게 한다.
    if user is not None and user.password_hash is not None:
        password_ok = verify_password(password, user.password_hash)
    else:
        verify_password(password, DUMMY_PASSWORD_HASH)
        password_ok = False

    # 이메일 없음·비번 불일치·탈퇴를 구분하지 않고 전부 같은 401.
    if user is None or not password_ok or user.deleted_at is not None:
        raise HTTPException(status_code=401, detail=_LOGIN_FAILED)

    return _issue_tokens(user)


@router.post("/auth/refresh", response_model=RefreshTokenResponse, summary="토큰 재발급")
def refresh(payload: RefreshRequest, db: DbSession) -> RefreshTokenResponse:
    try:
        user_id = decode_token(payload.refresh_token, "refresh")
    except TokenError:
        raise HTTPException(status_code=401, detail=_TOKEN_INVALID) from None

    user = db.get(User, user_id)
    if user is None or user.deleted_at is not None:
        raise HTTPException(status_code=401, detail=_TOKEN_INVALID)

    return RefreshTokenResponse(
        access_token=create_access_token(user.id),
        # 회전 없음 — 받은 refresh token 을 그대로 돌려준다. 새로 서명하면 14일이
        # 매 재발급마다 무한 연장된다(auth.md 확정).
        refresh_token=payload.refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRES_IN,
    )
