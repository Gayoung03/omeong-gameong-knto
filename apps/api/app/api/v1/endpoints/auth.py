"""이메일 인증 엔드포인트 (docs/api/auth.md 확정 명세).

이 단계(Phase 3)는 **토큰을 발급만** 한다. 발급된 access token 을 실제로 검증해
사용자를 식별하는 전환(`get_current_user` 교체)은 Phase 4 다 — 프론트 영향을
격리하려고 분리했다. 그래서 `logout` 은 아직 개발용 고정 사용자(스텁)를 받는다.

소셜 로그인(kakao·google)은 Phase 5 다. 여기엔 이메일 경로만 있다.
"""

from dataclasses import dataclass
from datetime import timedelta
from typing import Annotated
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.core.config import settings
from app.core.security import (
    ACCESS_TOKEN_EXPIRES_IN,
    DUMMY_PASSWORD_HASH,
    LEEWAY_SECONDS,
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_claims,
    decode_token,
    encode_token,
    hash_password,
    verify_password,
)
from app.db.models import User
from app.db.models.enums import AuthProvider
from app.db.session import get_db
from app.integrations.social_auth.kakao import (
    KakaoOAuthClient,
    SocialAuthError,
    SocialProfile,
    SocialProviderUnavailable,
    get_kakao_client,
)
from app.schemas.auth import (
    AuthUser,
    CheckEmailResponse,
    LinkRequiredResponse,
    LoginRequest,
    NormalizedEmail,
    RefreshRequest,
    RefreshTokenResponse,
    SignupRequest,
    SocialCompleteRequest,
    SocialExchangeRequest,
    SocialTokenResponse,
    TokenResponse,
)
from app.services import pets as pet_service
from app.services.social_auth import (
    consume_jti_once,
    create_social_user,
    link_social_account,
    mask_email,
    resolve_exchange,
)
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


@router.get("/auth/check-email", response_model=CheckEmailResponse, summary="이메일 중복 확인")
def check_email(
    email: Annotated[NormalizedEmail, Query(description="확인할 이메일")],
    db: DbSession,
) -> CheckEmailResponse:
    # 탈퇴 계정 이메일도 soft delete 라 행이 남아 available=false (재가입 차단과 일치).
    exists = db.scalar(select(User.id).where(User.email == email))
    return CheckEmailResponse(available=exists is None)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT, summary="로그아웃")
def logout(current_user: CurrentUser) -> Response:
    """서버 무효화 없음(auth.md) — 토큰 삭제는 앱이 한다. 성공 신호(204)만 돌려준다.

    지금은 개발용 고정 사용자(스텁)를 받는다. 실제 access token 검증 전환은 Phase 4.
    """
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# 소셜 로그인 (카카오) — 서버 콜백 방식 (docs/api/auth.md 소셜 절)
# ---------------------------------------------------------------------------

_STATE_TTL = timedelta(minutes=10)
_EXCHANGE_TTL = timedelta(seconds=60)
_LINK_TTL = timedelta(minutes=5)

_SOCIAL_AUTH_FAILED = "소셜 인증에 실패했습니다"


def _require_kakao(provider: str) -> None:
    # 구글은 콘솔 키 대기로 후순위 — 지금은 kakao 만 허용.
    if provider != "kakao":
        raise HTTPException(status_code=422, detail="지원하지 않는 소셜 제공처입니다")


#: HTTP(S)는 호스트 개념이 있어 정확 비교하고, 커스텀 스킴(exp·omeonggameong 등)은
#: 호스트가 없어 scheme 만 정확 비교한다.
_WEB_SCHEMES = frozenset({"http", "https"})


@dataclass(frozen=True)
class _ReturnUrlRule:
    scheme: str
    host: str | None  # HTTP(S)에서만 의미. 커스텀 스킴은 None.
    port: int | None  # None 이면 포트 무관.


def _parse_return_rule(entry: str) -> _ReturnUrlRule | None:
    """허용 목록 항목(예: `http://localhost`, `exp://`, `https://app.example`) → 규칙."""
    parsed = urlsplit(entry.strip())
    scheme = parsed.scheme.lower()
    if not scheme:
        return None
    host = (parsed.hostname or "").lower() or None
    # HTTP(S) 규칙인데 호스트가 없으면(예: `http://`) 아무 호스트나 통과시키는 위험한
    # 규칙이 되므로 버린다.
    if scheme in _WEB_SCHEMES and host is None:
        return None
    return _ReturnUrlRule(scheme=scheme, host=host, port=parsed.port)


def _allowed_return_rules() -> list[_ReturnUrlRule]:
    raw = settings.oauth_return_url_prefixes
    if raw:
        entries = [entry for entry in raw.split(",") if entry.strip()]
    elif settings.environment == "local":
        entries = ["exp://", "http://localhost"]
    else:
        entries = []
    return [rule for entry in entries if (rule := _parse_return_rule(entry)) is not None]


def _validate_return_url(return_url: str) -> None:
    """returnUrl 을 허용 목록과 **호스트 정확 비교**로 검증한다.

    `startswith` 는 `http://localhost.evil.com`·`https://app.example.attacker.com`·
    `http://localhost@evil.com` 같은 서브도메인·서픽스·userinfo 우회를 통과시켜
    피해자 code 를 탈취당할 수 있다. `urlsplit` 으로 파싱해 scheme·host(+명시 포트)를
    정확히 대조한다(validators.validate_image_url 과 같은 방식).
    """
    parsed = urlsplit(return_url)
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower() or None

    for rule in _allowed_return_rules():
        if rule.scheme != scheme:
            continue
        if scheme in _WEB_SCHEMES:
            if rule.host == host and (rule.port is None or rule.port == parsed.port):
                return
        else:
            # 커스텀 스킴은 호스트가 없어 scheme 정확 비교로 충분.
            return

    raise HTTPException(status_code=422, detail="허용되지 않은 returnUrl 입니다")


def _profile_claims(profile: SocialProfile) -> dict:
    return {
        "provider": profile.provider,
        "puid": profile.provider_user_id,
        "email": profile.email,
        "nickname": profile.nickname,
        "image": profile.profile_image_url,
    }


def _profile_from_claims(claims: dict) -> SocialProfile:
    return SocialProfile(
        provider=claims["provider"],
        provider_user_id=claims["puid"],
        email=claims.get("email"),
        nickname=claims.get("nickname"),
        profile_image_url=claims.get("image"),
    )


def _social_tokens(user: User, *, is_new_user: bool) -> SocialTokenResponse:
    return SocialTokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        expires_in=ACCESS_TOKEN_EXPIRES_IN,
        user=_auth_user(user),
        is_new_user=is_new_user,
    )


@router.get("/auth/{provider}/authorize", summary="소셜 로그인 시작")
def social_authorize(
    provider: str,
    return_url: Annotated[str, Query(alias="returnUrl")],
    kakao: Annotated[KakaoOAuthClient, Depends(get_kakao_client)],
) -> RedirectResponse:
    """returnUrl 을 검증하고 서명 state 를 발급해 카카오 인가 페이지로 302."""
    _require_kakao(provider)
    _validate_return_url(return_url)
    state = encode_token({"returnUrl": return_url}, "oauth_state", _STATE_TTL)
    url = kakao.authorize_url(state, settings.kakao_redirect_uri)
    return RedirectResponse(url, status_code=302)


@router.get("/auth/{provider}/callback", summary="소셜 콜백 수신")
def social_callback(
    provider: str,
    code: Annotated[str, Query()],
    state: Annotated[str, Query()],
    kakao: Annotated[KakaoOAuthClient, Depends(get_kakao_client)],
) -> RedirectResponse:
    """state 검증 → 프로필 조회 → 일회용 교환 코드 발급 → returnUrl 로 302.

    교환 코드에는 **프로필**을 담고, 계정 판정은 `/auth/social/exchange` 가 그 시점의
    DB 로 수행한다(판정 시점을 늦춰 콜백~교환 사이 상태 변화·TOCTOU 를 줄인다).
    """
    _require_kakao(provider)
    try:
        claims = decode_claims(state, "oauth_state")
    except TokenError:
        raise HTTPException(status_code=422, detail="state 가 유효하지 않습니다") from None

    # state 는 1회성(CSRF·재생 방지). 재사용은 거부한다.
    if not consume_jti_once(claims["jti"], _STATE_TTL.total_seconds() + LEEWAY_SECONDS):
        raise HTTPException(status_code=422, detail="state 가 이미 사용되었습니다")

    return_url = claims.get("returnUrl", "")
    _validate_return_url(return_url)

    try:
        profile = kakao.fetch_profile(code, settings.kakao_redirect_uri)
    except SocialAuthError:
        raise HTTPException(status_code=401, detail=_SOCIAL_AUTH_FAILED) from None
    except SocialProviderUnavailable:
        raise HTTPException(status_code=502, detail="소셜 제공처가 응답하지 않습니다") from None

    exchange_code = encode_token(_profile_claims(profile), "exchange", _EXCHANGE_TTL)
    separator = "&" if "?" in return_url else "?"
    return RedirectResponse(f"{return_url}{separator}code={exchange_code}", status_code=302)


@router.post("/auth/social/exchange", summary="교환 코드를 우리 토큰으로 교환")
def social_exchange(
    payload: SocialExchangeRequest, db: DbSession
) -> SocialTokenResponse | LinkRequiredResponse:
    try:
        claims = decode_claims(payload.code, "exchange")
    except TokenError:
        raise HTTPException(status_code=401, detail="교환 코드가 유효하지 않습니다") from None
    if not consume_jti_once(claims["jti"], _EXCHANGE_TTL.total_seconds() + LEEWAY_SECONDS):
        raise HTTPException(status_code=401, detail="교환 코드가 이미 사용되었습니다")

    profile = _profile_from_claims(claims)
    try:
        outcome = resolve_exchange(db, profile)
    except SocialAuthError:
        raise HTTPException(status_code=401, detail=_SOCIAL_AUTH_FAILED) from None

    if outcome.kind == "link_required":
        link_token = encode_token(
            {**_profile_claims(profile), "email": outcome.link_email}, "link", _LINK_TTL
        )
        return LinkRequiredResponse(
            link_token=link_token, masked_email=mask_email(outcome.link_email or "")
        )

    db.commit()
    return _social_tokens(outcome.user, is_new_user=outcome.is_new_user)


@router.post("/auth/social/complete", summary="소셜 연동 확정 또는 별도 계정")
def social_complete(payload: SocialCompleteRequest, db: DbSession) -> SocialTokenResponse:
    try:
        claims = decode_claims(payload.link_token, "link")
    except TokenError:
        raise HTTPException(status_code=401, detail="링크 토큰이 유효하지 않습니다") from None

    profile = _profile_from_claims(claims)

    if payload.action == "link":
        email = claims.get("email")
        user = db.scalar(select(User).where(User.email == email)) if email else None
        password = payload.password.get_secret_value() if payload.password else ""
        # 비밀번호 확인이 이메일 소유 증명을 대신한다(선점 가입 계정 탈취 차단).
        # 비밀번호 실패 시에는 링크 토큰을 **소비하지 않는다** — 사용자가 다시 시도하거나
        # `separate` 로 별도 계정을 선택할 수 있어야 한다(선점 공격 회복 경로).
        if (
            user is None
            or user.deleted_at is not None
            or user.password_hash is None
            or not verify_password(password, user.password_hash)
        ):
            raise HTTPException(status_code=401, detail="비밀번호가 일치하지 않습니다")
        _consume_link_token_or_401(claims["jti"])
        try:
            link_social_account(db, user, profile)
        except SocialAuthError:
            raise HTTPException(status_code=401, detail=_SOCIAL_AUTH_FAILED) from None
        db.commit()
        return _social_tokens(user, is_new_user=False)

    # action == "separate" — 연동하지 않고 별도 계정(email=null) 생성.
    _consume_link_token_or_401(claims["jti"])
    try:
        user = create_social_user(db, profile)
    except SocialAuthError:
        raise HTTPException(status_code=401, detail=_SOCIAL_AUTH_FAILED) from None
    db.commit()
    return _social_tokens(user, is_new_user=True)


def _consume_link_token_or_401(jti: str) -> None:
    # 링크 토큰은 **성공 시에만** 1회 소비한다(위 링크 실패 경로 주석 참고).
    if not consume_jti_once(jti, _LINK_TTL.total_seconds() + LEEWAY_SECONDS):
        raise HTTPException(status_code=401, detail="링크 토큰이 이미 사용되었습니다")
