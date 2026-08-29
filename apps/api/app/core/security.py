"""JWT 발급·검증과 비밀번호 해시.

## 규약 (docs/api/auth.md "JWT 구현 규약" 확정)

- 서명은 **HS256 고정**. 검증 시 `algorithms=["HS256"]` 를 명시한다 — 명시하지
  않으면 토큰 헤더의 `alg` 를 그대로 믿어 알고리즘 혼동 공격(`alg: none`, RS→HS
  키 혼동)에 노출된다.
- 키는 `settings.secret_key`(없으면 기동 실패, Phase 1).
- 클레임: `sub`(user id 문자열)·`typ`(`access`|`refresh`)·`jti`·`iat`·`exp`.
- clock skew 여유 `leeway` 10초.
- **만료·위조·typ 불일치·sub 비UUID 를 전부 같은 예외(`TokenError`)로 통일**한다.
  외부에는 전부 같은 401 로 나가야 한다 — 어느 쪽인지 알려주면 위조 시도에 힌트가
  된다. 내부 로그만 원인을 구분한다.

비밀번호는 argon2(argon2-cffi 기본 파라미터)로 해시한다.
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import settings

logger = logging.getLogger(__name__)

ALGORITHM = "HS256"
LEEWAY_SECONDS = 10

#: access 30분 / refresh 14일 (auth.md 확정).
ACCESS_TOKEN_TTL = timedelta(minutes=30)
REFRESH_TOKEN_TTL = timedelta(days=14)
#: 응답 `expiresIn` — 앱이 만료 시각을 직접 계산하지 않도록 서버가 초로 내려준다.
ACCESS_TOKEN_EXPIRES_IN = int(ACCESS_TOKEN_TTL.total_seconds())

TokenType = Literal["access", "refresh"]

_password_hasher = PasswordHasher()

#: 존재하지 않는 이메일로 로그인해도 해시 검증 비용을 동일하게 치르기 위한 더미
#: 해시(타이밍 공격으로 "가입된 이메일"을 알아내지 못하게). 모듈 로드 시 한 번 만든다.
DUMMY_PASSWORD_HASH = _password_hasher.hash("*timing-guard*")


class TokenError(Exception):
    """토큰이 유효하지 않다 — 만료·위조·typ 불일치·sub 비UUID 를 모두 포함한다."""


def _create_token(user_id: uuid.UUID, typ: TokenType, ttl: timedelta) -> str:
    now = datetime.now(UTC)
    claims = {
        "sub": str(user_id),
        "typ": typ,
        "jti": uuid.uuid4().hex,
        "iat": int(now.timestamp()),
        "exp": int((now + ttl).timestamp()),
    }
    return jwt.encode(claims, settings.secret_key, algorithm=ALGORITHM)


def create_access_token(user_id: uuid.UUID) -> str:
    return _create_token(user_id, "access", ACCESS_TOKEN_TTL)


def create_refresh_token(user_id: uuid.UUID) -> str:
    return _create_token(user_id, "refresh", REFRESH_TOKEN_TTL)


def decode_token(token: str, expected_typ: TokenType) -> uuid.UUID:
    """토큰을 검증하고 subject(user id)를 UUID 로 돌려준다.

    서명·만료·`typ` 일치·`sub` 의 UUID 파싱까지 확인한다. 어느 하나라도 어긋나면
    전부 `TokenError` — 외부에는 같은 401 로 나가야 한다.
    """
    try:
        claims = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[ALGORITHM],
            leeway=LEEWAY_SECONDS,
        )
    except jwt.PyJWTError as error:
        logger.info("JWT 검증 실패: %s", type(error).__name__)
        raise TokenError from error

    if claims.get("typ") != expected_typ:
        logger.info("JWT typ 불일치: expected=%s", expected_typ)
        raise TokenError

    try:
        return uuid.UUID(claims.get("sub"))
    except (ValueError, TypeError) as error:
        logger.info("JWT sub 가 UUID 가 아님")
        raise TokenError from error


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """비밀번호가 해시와 맞는지 확인한다. 어떤 실패든 조용히 False."""
    try:
        _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False
    return True
