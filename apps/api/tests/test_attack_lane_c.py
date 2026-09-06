"""비밀번호 재설정 공격 — 레인 C: 시도횟수 상한 + 재발급 우회.

레인 C 에이전트가 세션 한도로 중단돼 메인 세션이 대신 완성했다. 판정은
정확한 상태코드 + negative control 로 "테스트가 껍데기가 아님"을 증명한다.

실행:
    TEST_DATABASE_URL='postgresql+psycopg://omeong:omeong@localhost:5432/omeong_test_c' \
        uv run pytest tests/test_attack_lane_c.py -v -s
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.db.models import PasswordResetCode, User
from app.db.models.enums import AuthProvider

REQUEST_URL = "/api/v1/auth/password-reset/request"
VERIFY_URL = "/api/v1/auth/password-reset/verify"
CONFIRM_URL = "/api/v1/auth/password-reset/confirm"
OLD_PW = "old-password-123"
NEW_PW = "new-password-456"
CODE = "123456"
WRONG = "000000"


def _user(db: Session) -> User:
    u = User(
        id=uuid.uuid4(),
        nickname="C피해자",
        email=f"{uuid.uuid4().hex}@example.com",
        password_hash=hash_password(OLD_PW),
        auth_provider=AuthProvider.LOCAL,
    )
    db.add(u)
    db.flush()
    return u


def _row(db: Session, u: User) -> PasswordResetCode | None:
    """지금 살아 있는(미사용) 코드를 집는다.

    테스트는 한 트랜잭션 안에서 돌아 PostgreSQL `now()`(=트랜잭션 시작 시각)가
    같은 값을 주므로, 한 유저의 코드 행들은 created_at 이 동점이라 시각 정렬이
    비결정적이다. 살아 있는 코드는 회원당 최대 하나라 `used_at IS NULL` 로 집으면
    재발급 뒤에도 항상 방금 만든 코드가 잡힌다.
    """
    return db.scalar(
        select(PasswordResetCode)
        .where(PasswordResetCode.user_id == u.id, PasswordResetCode.used_at.is_(None))
        .order_by(PasswordResetCode.created_at.desc())
    )


def _issue(client: TestClient, db: Session, u: User) -> PasswordResetCode:
    client.post(REQUEST_URL, json={"email": u.email})
    r = _row(db, u)
    assert r is not None
    r.code_hash = hash_password(CODE)
    db.flush()
    return r


# --- 무차별 대입 상한 -------------------------------------------------------


def test_무차별_대입_상한_넘으면_맞는_코드도_죽는다(anon_client: TestClient, db: Session) -> None:
    u = _user(db)
    _issue(anon_client, db, u)
    limit = int(settings.password_reset_max_attempts)

    for _ in range(limit):
        r = anon_client.post(
            CONFIRM_URL, json={"email": u.email, "code": WRONG, "newPassword": NEW_PW}
        )
        assert r.status_code == 400

    over = anon_client.post(
        CONFIRM_URL, json={"email": u.email, "code": CODE, "newPassword": NEW_PW}
    )
    assert over.status_code == 429  # 상한 넘긴 코드는 맞는 코드조차 통과 못 함
    db.refresh(u)
    assert verify_password(OLD_PW, u.password_hash)


def test_상한이_실재함_negative_control(
    anon_client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """상한을 크게 열면 무차별 대입이 성공한다 → 위 테스트가 껍데기가 아님을 증명."""
    monkeypatch.setattr(settings, "password_reset_max_attempts", 1000)
    u = _user(db)
    _issue(anon_client, db, u)

    for _ in range(20):
        assert (
            anon_client.post(
                CONFIRM_URL, json={"email": u.email, "code": WRONG, "newPassword": NEW_PW}
            ).status_code
            == 400
        )

    # 20회 틀려도 코드가 안 죽음 → 맞는 코드로 204 (상한이 없으면 뚫린다)
    assert (
        anon_client.post(
            CONFIRM_URL, json={"email": u.email, "code": CODE, "newPassword": NEW_PW}
        ).status_code
        == 204
    )


# --- 재발급 attempt_count 리셋 우회 -----------------------------------------


def test_재발급하면_시도횟수가_0으로_리셋된다(anon_client: TestClient, db: Session) -> None:
    u = _user(db)
    r1 = _issue(anon_client, db, u)
    limit = int(settings.password_reset_max_attempts)

    for _ in range(limit):
        anon_client.post(CONFIRM_URL, json={"email": u.email, "code": WRONG, "newPassword": NEW_PW})
    db.refresh(r1)
    assert r1.attempt_count >= limit  # 소진됨

    anon_client.post(REQUEST_URL, json={"email": u.email})  # 재발급
    r2 = _row(db, u)
    assert r2.id != r1.id
    assert r2.attempt_count == 0  # 새 코드는 시도횟수가 리셋됨
    assert r2.used_at is None


def test_시간당_최대_추측_횟수_실측(anon_client: TestClient, db: Session) -> None:
    """재발급으로 코드당 상한이 되살아나므로, 실질 방어는 '시간당 발급 상한'뿐이다.

    시간당 최대 추측 = (시간당 발급 코드 수) × (코드당 시도 상한). 100만 조합 대비
    이 값이 얼마나 작은지 실측한다.
    """
    u = _user(db)
    hourly = int(settings.password_reset_hourly_limit)
    per_code = int(settings.password_reset_max_attempts)

    for _ in range(hourly * 3):  # 상한의 3배 재발급 시도
        anon_client.post(REQUEST_URL, json={"email": u.email})

    created = db.scalar(
        select(func.count(PasswordResetCode.id)).where(PasswordResetCode.user_id == u.id)
    )
    assert created <= hourly  # 시간당 발급이 상한에서 멈춤

    max_guesses = created * per_code
    print(
        f"[레인C] 시간당 최대 추측 = {max_guesses}회 "
        f"(발급 {created} × 코드당 {per_code}) / 6자리 조합 1,000,000"
    )
    assert max_guesses <= hourly * per_code


# --- verify vs confirm 시도횟수 계산 ----------------------------------------


def test_맞는_verify는_시도횟수를_안_센다(anon_client: TestClient, db: Session) -> None:
    u = _user(db)
    _issue(anon_client, db, u)
    for _ in range(10):
        assert (
            anon_client.post(VERIFY_URL, json={"email": u.email, "code": CODE}).status_code == 204
        )
    r = _row(db, u)
    db.refresh(r)
    assert r.attempt_count == 0  # 맞는 verify 는 카운트 안 함(정상 사용자가 상한에 안 걸리게)
    assert r.used_at is None  # verify 는 코드를 소모하지 않음


def test_틀린_verify는_세고_상한도_건다(anon_client: TestClient, db: Session) -> None:
    u = _user(db)
    _issue(anon_client, db, u)
    limit = int(settings.password_reset_max_attempts)
    for _ in range(limit):
        assert (
            anon_client.post(VERIFY_URL, json={"email": u.email, "code": WRONG}).status_code == 400
        )
    # 상한 후엔 맞는 코드 verify 도 429
    assert anon_client.post(VERIFY_URL, json={"email": u.email, "code": CODE}).status_code == 429
