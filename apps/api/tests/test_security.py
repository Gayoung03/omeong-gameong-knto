"""JWT·비밀번호 해시 코어 단위 테스트 (DB 불필요)."""

import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.config import settings
from app.core.security import (
    ALGORITHM,
    LEEWAY_SECONDS,
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    issued_before,
    verify_password,
)


def _encode(claims: dict) -> str:
    return jwt.encode(claims, settings.secret_key, algorithm=ALGORITHM)


def _base_claims(typ: str, *, exp_delta: timedelta = timedelta(minutes=5)) -> dict:
    now = datetime.now(UTC)
    return {
        "sub": str(uuid.uuid4()),
        "typ": typ,
        "jti": uuid.uuid4().hex,
        "iat": int(now.timestamp()),
        "exp": int((now + exp_delta).timestamp()),
    }


# --- 발급·검증 왕복 -----------------------------------------------------------


def test_access_토큰_왕복() -> None:
    user_id = uuid.uuid4()
    token = create_access_token(user_id)
    assert decode_token(token, "access") == user_id


def test_refresh_토큰_왕복() -> None:
    user_id = uuid.uuid4()
    token = create_refresh_token(user_id)
    assert decode_token(token, "refresh") == user_id


# --- 실패 경로: 전부 같은 TokenError ------------------------------------------


def test_만료된_토큰은_거부한다() -> None:
    # leeway(10초)보다 확실히 지난 과거 만료.
    token = _encode(_base_claims("access", exp_delta=-timedelta(seconds=LEEWAY_SECONDS + 60)))
    with pytest.raises(TokenError):
        decode_token(token, "access")


def test_typ_교차_사용은_거부한다() -> None:
    access = create_access_token(uuid.uuid4())
    with pytest.raises(TokenError):
        decode_token(access, "refresh")

    refresh = create_refresh_token(uuid.uuid4())
    with pytest.raises(TokenError):
        decode_token(refresh, "access")


def test_서명_위조는_거부한다() -> None:
    forged = jwt.encode(_base_claims("access"), "wrong-secret-key", algorithm=ALGORITHM)
    with pytest.raises(TokenError):
        decode_token(forged, "access")


def test_변조된_토큰은_거부한다() -> None:
    token = create_access_token(uuid.uuid4())
    tampered = token[:-3] + ("aaa" if not token.endswith("aaa") else "bbb")
    with pytest.raises(TokenError):
        decode_token(tampered, "access")


def test_sub가_UUID가_아니면_거부한다() -> None:
    claims = _base_claims("access")
    claims["sub"] = "not-a-uuid"
    token = _encode(claims)
    with pytest.raises(TokenError):
        decode_token(token, "access")


# --- 비밀번호 해시 -----------------------------------------------------------


def test_해시_왕복과_불일치() -> None:
    digest = hash_password("올바른비밀번호")
    assert digest != "올바른비밀번호"  # 평문 저장 아님
    assert verify_password("올바른비밀번호", digest) is True
    assert verify_password("틀린비밀번호", digest) is False


def test_망가진_해시는_False() -> None:
    # DB 에 든 해시가 argon2 형식이 아닐 때(손상 등) 예외로 터지지 않고 False.
    assert verify_password("anything", "not-a-valid-argon2-hash") is False


# --- 비밀번호 변경 시 기존 토큰 무효화 (issued_before) -------------------------


def test_비밀번호를_바꾼_적_없으면_아무_토큰도_무효가_아니다() -> None:
    claims = {"iat": int(datetime.now(UTC).timestamp())}
    assert issued_before(claims, None) is False


def test_변경_이전에_발급된_토큰은_무효다() -> None:
    changed_at = datetime.now(UTC)
    claims = {"iat": int((changed_at - timedelta(minutes=5)).timestamp())}
    assert issued_before(claims, changed_at) is True


def test_변경_이후에_발급된_토큰은_유효하다() -> None:
    changed_at = datetime.now(UTC)
    claims = {"iat": int((changed_at + timedelta(minutes=5)).timestamp())}
    assert issued_before(claims, changed_at) is False


def test_iat가_없는_토큰은_무효로_본다() -> None:
    # 우리가 발급한 토큰에는 항상 있다 — 없다는 건 정상 경로가 아니다.
    assert issued_before({}, datetime.now(UTC)) is True
    assert issued_before({"iat": "언제인지몰라"}, datetime.now(UTC)) is True
