"""비밀번호 재설정 공격 — 레인 B: 코드 수명주기 (재사용·만료).

레인 B 에이전트가 세션 한도로 중단돼 메인 세션이 대신 완성했다. 판정은
정확한 상태코드 + negative/positive control 로 "테스트가 껍데기가 아님"을 증명한다.

실행:
    TEST_DATABASE_URL='postgresql+psycopg://omeong:omeong@localhost:5432/omeong_test_b' \
        uv run pytest tests/test_attack_lane_b.py -v
"""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.db.models import PasswordResetCode, User
from app.db.models.enums import AuthProvider

REQUEST_URL = "/api/v1/auth/password-reset/request"
VERIFY_URL = "/api/v1/auth/password-reset/verify"
CONFIRM_URL = "/api/v1/auth/password-reset/confirm"
OLD_PW = "old-password-123"
NEW_PW = "new-password-456"
CODE = "123456"


def _user(db: Session) -> User:
    u = User(
        id=uuid.uuid4(),
        nickname="B피해자",
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
    """정상 발급 후 code_hash 를 아는 값으로 덮어써 평문 코드를 확보한다."""
    client.post(REQUEST_URL, json={"email": u.email})
    r = _row(db, u)
    assert r is not None
    r.code_hash = hash_password(CODE)
    db.flush()
    return r


# --- 재사용 -----------------------------------------------------------------


def test_쓴_코드_재사용_차단(anon_client: TestClient, db: Session) -> None:
    u = _user(db)
    _issue(anon_client, db, u)

    first = anon_client.post(
        CONFIRM_URL, json={"email": u.email, "code": CODE, "newPassword": NEW_PW}
    )
    assert first.status_code == 204
    db.refresh(u)
    assert verify_password(NEW_PW, u.password_hash)  # 실제로 바뀜(positive)

    second = anon_client.post(
        CONFIRM_URL, json={"email": u.email, "code": CODE, "newPassword": "other-pw-789"}
    )
    assert second.status_code == 400
    assert second.json()["detail"]
    db.refresh(u)
    assert verify_password(NEW_PW, u.password_hash)  # 두 번째는 안 먹힘

    # positive control: 새 코드는 같은 경로로 정상 204
    _issue(anon_client, db, u)
    third = anon_client.post(
        CONFIRM_URL, json={"email": u.email, "code": CODE, "newPassword": "third-pw-000"}
    )
    assert third.status_code == 204


def test_쓴_코드_verify_차단(anon_client: TestClient, db: Session) -> None:
    u = _user(db)
    _issue(anon_client, db, u)
    assert (
        anon_client.post(
            CONFIRM_URL, json={"email": u.email, "code": CODE, "newPassword": NEW_PW}
        ).status_code
        == 204
    )
    # 쓴 코드로 verify → 400
    assert anon_client.post(VERIFY_URL, json={"email": u.email, "code": CODE}).status_code == 400


# --- 만료 -------------------------------------------------------------------


def test_만료_코드_confirm_차단(anon_client: TestClient, db: Session) -> None:
    u = _user(db)
    r = _issue(anon_client, db, u)
    r.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db.flush()

    resp = anon_client.post(
        CONFIRM_URL, json={"email": u.email, "code": CODE, "newPassword": NEW_PW}
    )
    assert resp.status_code == 400
    db.refresh(u)
    assert verify_password(OLD_PW, u.password_hash)

    # negative control: 만료시각을 미래로 되돌리면 같은 코드가 통과(204) → 만료검사 실재 증명
    r.expires_at = datetime.now(UTC) + timedelta(minutes=10)
    r.used_at = None
    db.flush()
    assert (
        anon_client.post(
            CONFIRM_URL, json={"email": u.email, "code": CODE, "newPassword": NEW_PW}
        ).status_code
        == 204
    )


def test_만료_코드_verify_차단(anon_client: TestClient, db: Session) -> None:
    u = _user(db)
    r = _issue(anon_client, db, u)
    r.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db.flush()
    assert anon_client.post(VERIFY_URL, json={"email": u.email, "code": CODE}).status_code == 400


def test_만료판정은_서버시각_기준_클라필드_무시(anon_client: TestClient, db: Session) -> None:
    """클라이언트가 body 에 시각 필드를 끼워넣어도 무시(extra=ignore)되고
    서버 DB 의 expires_at 만 본다."""
    u = _user(db)
    r = _issue(anon_client, db, u)
    r.expires_at = datetime.now(UTC) - timedelta(minutes=5)
    db.flush()

    payload = {
        "email": u.email,
        "code": CODE,
        "newPassword": NEW_PW,
        # 공격자가 심는 가짜 시각들 — 서버가 이걸 믿으면 만료를 우회당함
        "expiresAt": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        "now": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
    }
    assert anon_client.post(CONFIRM_URL, json=payload).status_code == 400
    db.refresh(u)
    assert verify_password(OLD_PW, u.password_hash)


# --- 새 코드 발급 시 이전 코드 폐기 ----------------------------------------


def test_재발급하면_이전_코드_폐기(anon_client: TestClient, db: Session) -> None:
    u = _user(db)
    anon_client.post(REQUEST_URL, json={"email": u.email})
    first = _row(db, u)
    assert first is not None and first.used_at is None

    anon_client.post(REQUEST_URL, json={"email": u.email})
    db.refresh(first)
    assert first.used_at is not None  # 이전 코드 폐기됨

    live = db.scalars(
        select(PasswordResetCode).where(
            PasswordResetCode.user_id == u.id, PasswordResetCode.used_at.is_(None)
        )
    ).all()
    assert len(live) == 1  # 살아있는 코드는 항상 최대 하나
