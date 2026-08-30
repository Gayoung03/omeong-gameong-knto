"""소셜 로그인 계정 판정·생성·연동 (docs/api/auth.md 소셜 절).

`(provider, provider_user_id)` 를 정본으로 로그인 여부를 가르고, 검증 이메일이 살아
있는 계정과 겹치면 **비밀번호 확인 후 연동**(자동 연동 금지 — local 가입에 이메일
소유 확인이 없어 선점 가입이 계정 탈취 경로가 된다). 신규 소셜 계정의 `email` 은
항상 null 로 둔다(선점·탈퇴 계정 부활 방지, users.email UNIQUE 회피).

트랜잭션 경계(commit)는 호출 엔드포인트가 갖는다 — 서비스는 add/flush 까지만.
"""

import secrets
import threading
import time
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import User, UserSocialAccount
from app.db.models.enums import AuthProvider
from app.integrations.social_auth.kakao import SocialAuthError, SocialProfile

# ---------------------------------------------------------------------------
# 일회용 토큰(jti) 소비 — 프로세스 메모리
# ---------------------------------------------------------------------------
#
# 교환 코드·링크 토큰의 재사용을 막는다. **프로세스 메모리라 다중 워커·재시작에서
# 1회성이 깨진다** — 데모는 단일 프로세스 전제. 더 강한 보장은 DB/Redis 가 필요하나
# 이번 범위(스키마 추가 금지)에선 제외한다(worklog 에 한계 명시).
_consumed_jti: dict[str, float] = {}
#: 체크-후-설정을 원자화한다. 동기 엔드포인트는 스레드풀에서 병렬 실행되므로, Lock
#: 없이는 같은 jti 로 온 두 요청이 둘 다 "미소비"로 읽고 둘 다 통과할 수 있다(TOCTOU).
_consumed_jti_lock = threading.Lock()


def consume_jti_once(jti: str, ttl_seconds: float) -> bool:
    """jti 를 1회만 소비 처리한다. 이미 썼으면 False. 체크-설정은 Lock 으로 원자화."""
    now = time.monotonic()
    with _consumed_jti_lock:
        for key in [key for key, expiry in _consumed_jti.items() if expiry <= now]:
            del _consumed_jti[key]
        if jti in _consumed_jti:
            return False
        _consumed_jti[jti] = now + ttl_seconds
        return True


# ---------------------------------------------------------------------------
# 콜백 프로필 임시 보관 — 참조 id 로만 교환 코드에 싣는다
# ---------------------------------------------------------------------------
#
# 교환 코드는 returnUrl 쿼리스트링(브라우저 히스토리·서버 access log)에 노출된다.
# 여기에 email·nickname 같은 PII 를 JWT 클레임으로 실으면 그대로 새므로, 프로필은
# 서버 메모리에 잠깐 두고 코드에는 불투명한 참조 id 만 담는다. (프로세스 메모리라
# 다중 워커·재시작 한계는 consume_jti_once 와 동일 — 단일 프로세스 데모 전제.)
_pending_profiles: dict[str, tuple[SocialProfile, float]] = {}
_pending_profiles_lock = threading.Lock()


def store_pending_profile(profile: SocialProfile, ttl_seconds: float) -> str:
    """프로필을 서버에 잠깐 보관하고 참조 id 를 돌려준다."""
    ref = secrets.token_urlsafe(16)
    now = time.monotonic()
    with _pending_profiles_lock:
        for key in [k for k, (_, expiry) in _pending_profiles.items() if expiry <= now]:
            del _pending_profiles[key]
        _pending_profiles[ref] = (profile, now + ttl_seconds)
    return ref


def take_pending_profile(ref: str) -> SocialProfile | None:
    """참조 id 로 보관된 프로필을 **1회만** 꺼낸다. 없거나 만료면 None."""
    now = time.monotonic()
    with _pending_profiles_lock:
        entry = _pending_profiles.pop(ref, None)
    if entry is None:
        return None
    profile, expiry = entry
    return profile if expiry > now else None


# ---------------------------------------------------------------------------
# 판정·생성·연동
# ---------------------------------------------------------------------------


@dataclass
class SocialOutcome:
    kind: Literal["login", "link_required", "new_account"]
    user: User | None = None
    is_new_user: bool = False
    link_email: str | None = None


def find_social_account(
    db: Session, provider: str, provider_user_id: str
) -> UserSocialAccount | None:
    return db.scalar(
        select(UserSocialAccount).where(
            UserSocialAccount.provider == AuthProvider(provider),
            UserSocialAccount.provider_user_id == provider_user_id,
        )
    )


def resolve_exchange(db: Session, profile: SocialProfile) -> SocialOutcome:
    """교환 시점에 최신 DB 로 판정한다(add/flush 까지, commit 은 호출자).

    ① (provider, id) 가 연결돼 있으면 로그인 — 단 소유 계정이 탈퇴면 401.
    ② 없고 **검증 이메일** = 살아 있는 계정이면 linkRequired.
    ③ 그 외(무이메일·미검증·탈퇴 계정 이메일 일치)면 새 계정(email=null) 생성.
    """
    account = find_social_account(db, profile.provider, profile.provider_user_id)
    if account is not None:
        user = db.get(User, account.user_id)
        if user is None or user.deleted_at is not None:
            # 탈퇴 계정의 소셜 재로그인 차단(탈퇴 이메일 재가입 차단과 같은 규칙).
            raise SocialAuthError("탈퇴한 계정입니다")
        return SocialOutcome(kind="login", user=user)

    if profile.email:
        existing = db.scalar(select(User).where(User.email == profile.email))
        if existing is not None and existing.deleted_at is None:
            return SocialOutcome(kind="link_required", link_email=profile.email)
        # 탈퇴 계정 이메일 일치는 여기로 떨어져 새 계정(email=null)이 된다.

    user = create_social_user(db, profile)
    return SocialOutcome(kind="new_account", user=user, is_new_user=True)


def create_social_user(db: Session, profile: SocialProfile) -> User:
    """소셜 신규 계정 + 연결 행. email 은 항상 null.

    `(provider, provider_user_id)` UNIQUE 경합(동시 콜백)은 IntegrityError 로 받아
    이미 만들어진 계정으로 로그인한다.
    """
    provider = AuthProvider(profile.provider)
    user = User(
        email=None,
        nickname=profile.nickname or "여행자",
        profile_image_url=profile.profile_image_url,
        # authProvider 는 "최초 가입 수단" 기록.
        auth_provider=provider,
    )
    db.add(user)
    db.flush()

    db.add(
        UserSocialAccount(
            user_id=user.id, provider=provider, provider_user_id=profile.provider_user_id
        )
    )
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        existing = find_social_account(db, profile.provider, profile.provider_user_id)
        if existing is None:
            raise
        owner = db.get(User, existing.user_id)
        if owner is None or owner.deleted_at is not None:
            raise SocialAuthError("탈퇴한 계정입니다") from None
        return owner
    return user


def link_social_account(db: Session, user: User, profile: SocialProfile) -> None:
    """기존 계정에 소셜 수단을 붙인다. 경합/중복은 IntegrityError 로 받아 거부."""
    db.add(
        UserSocialAccount(
            user_id=user.id,
            provider=AuthProvider(profile.provider),
            provider_user_id=profile.provider_user_id,
        )
    )
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise SocialAuthError("이미 연동된 소셜 계정입니다") from None


def mask_email(email: str) -> str:
    """`traveler@example.com` → `tra*****@example.com` (auth.md 예시 형식)."""
    local, _, domain = email.partition("@")
    return f"{local[:3]}*****@{domain}"
