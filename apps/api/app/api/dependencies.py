"""Shared FastAPI dependencies.

## 인증 (Phase 4 — JWT 검증 전환)

`Authorization: Bearer <accessToken>` 이 있으면 **환경과 무관하게 항상 검증**한다
(만료·위조·`typ≠access`·탈퇴·`sub` 비UUID → 전부 401, 내부 로그만 원인 구분).

헤더가 없을 때만 갈린다: `environment == "local"` 이면 개발용 고정 사용자로 폴백하고
(프론트 로그인 연동 전에도 개발·시연 흐름이 안 깨지게), 그 외 환경은 401 이다.
**배포본에는 폴백이 존재하지 않는다.**

함수 이름과 반환 타입(`-> User`)은 그대로 유지한다 — 엔드포인트는 `CurrentUser`·
`OptionalUser` 를 쓰던 그대로이고, 테스트의 `dependency_overrides` 도 깨지지 않는다.
"""

import logging
import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import TokenError, decode_token_with_claims, issued_before
from app.db.models import User
from app.db.session import get_db

logger = logging.getLogger(__name__)

# 개발용 고정 사용자. scripts/seed_dev.py 가 이 id 로 계정을 심는다.
# 팀원 A 와 공유한 값이라 바꾸지 않는다.
DEV_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

_UNAUTHENTICATED = "인증이 필요합니다"

#: auto_error=False — 헤더가 없거나 Bearer 형식이 아니면 예외 대신 None 을 준다.
#: (없을 때의 처리를 우리가 직접 결정해야 하기 때문 — local 폴백 vs 401.)
_bearer_scheme = HTTPBearer(auto_error=False)

BearerCredentials = Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)]

#: 폴백 경고는 요청마다 찍히면 시끄러우므로 프로세스당 1회만 남긴다.
_dev_fallback_warned = False


def _warn_dev_fallback_once() -> None:
    global _dev_fallback_warned
    if not _dev_fallback_warned:
        logger.warning(
            "인증 헤더 없이 local 개발용 고정 사용자로 폴백합니다 (데모 D-7 제거 예정 — #141)"
        )
        _dev_fallback_warned = True


def _authenticate(db: Session, token: str) -> User:
    """access token 을 검증하고 살아 있는 사용자를 돌려준다. 어떤 실패든 401."""
    try:
        user_id, claims = decode_token_with_claims(token, "access")
    except TokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=_UNAUTHENTICATED
        ) from None
    user = db.get(User, user_id)
    # 탈퇴 계정은 토큰이 유효해도 401 (auth.md — 모든 인증 요청에서 deleted_at 확인).
    if user is None or user.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_UNAUTHENTICATED)
    # 비밀번호를 바꾸기 전에 발급된 토큰도 401 — 계정을 되찾은 사람이 비밀번호를
    # 바꿨는데 공격자의 세션이 남아 있으면 재설정 기능의 의미가 없다.
    if issued_before(claims, user.password_changed_at):
        logger.info("비밀번호 변경 이전 토큰 — user_id=%s", user.id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_UNAUTHENTICATED)
    return user


def get_current_user(
    db: Annotated[Session, Depends(get_db)], credentials: BearerCredentials
) -> User:
    """현재 로그인한 사용자. 헤더가 있으면 검증, 없으면 local 폴백 또는 401."""
    if credentials is not None:
        return _authenticate(db, credentials.credentials)

    # ------------------------------------------------------------------
    # 데모 D-7 제거 예정 — #141. 프론트 로그인 연동이 끝나면 이 블록을 지운다.
    # 헤더가 없을 때 local 개발에서만 고정 사용자로 폴백한다.
    if settings.environment == "local":
        _warn_dev_fallback_once()
        user = db.get(User, DEV_USER_ID)
        if user is not None and user.deleted_at is None:
            return user
    # ------------------------------------------------------------------

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_UNAUTHENTICATED)


# 엔드포인트에서 `current_user: CurrentUser` 한 줄로 쓴다.
CurrentUser = Annotated[User, Depends(get_current_user)]


def get_optional_user(
    db: Annotated[Session, Depends(get_db)], credentials: BearerCredentials
) -> User | None:
    """토큰이 없어도 되는 조회용 사용자.

    장소 조회는 비로그인도 할 수 있고, 로그인했을 때만 응답에 isFavorite 가
    채워진다(docs/api/places.md). 헤더가 **있으면** get_current_user 와 똑같이
    검증한다(잘못된 토큰은 401 — 있는데 틀린 건 조용히 넘기지 않는다). 헤더가
    없으면 401 대신 local=고정 사용자 / 그 외 환경=None 이다.
    """
    if credentials is not None:
        return _authenticate(db, credentials.credentials)

    # 데모 D-7 제거 예정 — #141. (get_current_user 폴백과 짝을 이룬다.)
    if settings.environment == "local":
        return db.get(User, DEV_USER_ID)
    return None


#: 엔드포인트에서 `current_user: OptionalUser` 한 줄로 쓴다. None 일 수 있다.
OptionalUser = Annotated[User | None, Depends(get_optional_user)]
