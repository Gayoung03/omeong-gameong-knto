"""비밀번호 재설정 — 적대적 공격 시나리오.

이 파일은 "기능이 되는가"가 아니라 **"공격이 통하는가"** 를 확인한다. 각 테스트는
공격자가 실제로 보낼 요청을 그대로 날리고, **막혀 있으면 통과** 하도록 단언을 건다.
그래서 여기서 실패하는 테스트 = 실제로 뚫리는 구멍이다.

돌리는 법(로컬 전용 PostgreSQL 을 가리켜야 한다 — 공유 RDS 아님):
    TEST_DATABASE_URL=postgresql+psycopg://omeong:omeong@localhost:5432/omeong \
        uv run pytest tests/test_password_reset_attack.py -v
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

OLD_PASSWORD = "old-password-123"
NEW_PASSWORD = "new-password-456"
PLANTED_CODE = "123456"


def _local_user(db: Session) -> User:
    user = User(
        id=uuid.uuid4(),
        nickname="피해자",
        email=f"{uuid.uuid4().hex}@example.com",
        password_hash=hash_password(OLD_PASSWORD),
        auth_provider=AuthProvider.LOCAL,
    )
    db.add(user)
    db.flush()
    return user


def _kakao_user(db: Session) -> User:
    user = User(
        id=uuid.uuid4(),
        nickname="카카오피해자",
        email=f"{uuid.uuid4().hex}@example.com",
        password_hash=None,
        auth_provider=AuthProvider.KAKAO,
        provider_user_id=uuid.uuid4().hex,
    )
    db.add(user)
    db.flush()
    return user


def _latest_code_row(db: Session, user: User) -> PasswordResetCode | None:
    return db.scalar(
        select(PasswordResetCode)
        .where(PasswordResetCode.user_id == user.id)
        .order_by(PasswordResetCode.created_at.desc())
    )


def _issue_planted_code(client: TestClient, db: Session, user: User) -> str:
    """정상 발급 경로로 코드를 하나 만들고, 그 해시를 아는 값으로 갈아끼운다."""
    client.post(REQUEST_URL, json={"email": user.email})
    row = _latest_code_row(db, user)
    assert row is not None
    row.code_hash = hash_password(PLANTED_CODE)
    db.flush()
    return PLANTED_CODE


# ---------------------------------------------------------------------------
# 공격 1 — 소셜 계정 이메일을 알면 안내 메일을 무제한으로 쏠 수 있는가
# ---------------------------------------------------------------------------


def test_공격_소셜계정_안내메일_폭탄(
    anon_client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """소셜 계정 이메일 하나로 request 를 난사하면 안내 메일이 몇 통 나가나.

    막혀 있다면(시간당 상한이 소셜 경로에도 걸린다면) 상한만큼에서 멈춰야 한다.
    상한 없이 요청 수만큼 나간다면 = 남의 메일함을 마음대로 채울 수 있는 구멍.
    """
    from app.services import password_reset

    sent: list[str] = []
    monkeypatch.setattr(
        password_reset, "send_email", lambda to, subject, body: sent.append(subject)
    )

    victim = _kakao_user(db)
    # settings 객체를 assert 에 직접 넣으면 pytest 실패 시 전체 repr(실 비밀값 포함)이
    # 로그에 덤프된다 — 평범한 int 로 먼저 뽑아 쓴다.
    limit = int(settings.password_reset_hourly_limit)
    blitz = limit * 4  # 상한의 4배를 쏴 본다

    for _ in range(blitz):
        assert anon_client.post(REQUEST_URL, json={"email": victim.email}).status_code == 202

    count = len(sent)
    assert count <= limit, (
        f"소셜 계정에 안내 메일이 {count}통 나갔다 (상한 {limit}). "
        f"시간당 상한이 소셜 경로에는 걸리지 않아 메일 폭탄이 가능하다."
    )


# ---------------------------------------------------------------------------
# 공격 2 — 로컬 계정에는 시간당 상한이 실제로 걸리는가
# ---------------------------------------------------------------------------


def test_공격_로컬계정_시간당_상한_우회(anon_client: TestClient, db: Session) -> None:
    """로컬 계정에 request 를 난사해도 코드 행은 상한 개수를 넘지 않아야 한다."""
    victim = _local_user(db)
    blitz = settings.password_reset_hourly_limit * 4

    for _ in range(blitz):
        anon_client.post(REQUEST_URL, json={"email": victim.email})

    created = db.scalar(
        select(func.count(PasswordResetCode.id)).where(PasswordResetCode.user_id == victim.id)
    )
    assert created <= settings.password_reset_hourly_limit, (
        f"코드가 {created}개 발급됐다 (상한 {settings.password_reset_hourly_limit}). "
        f"시간당 상한이 로컬 경로에서 뚫린다."
    )


# ---------------------------------------------------------------------------
# 공격 3 — 6자리 인증번호를 무차별 대입할 수 있는가
# ---------------------------------------------------------------------------


def test_공격_인증번호_무차별_대입(anon_client: TestClient, db: Session) -> None:
    """틀린 코드를 계속 넣어 상한을 넘긴 뒤, 맞는 코드가 여전히 통하는지 본다.

    상한을 넘긴 코드가 죽지 않으면 100만 개를 다 넣어보면 되니 6자리는 무의미해진다.
    """
    victim = _local_user(db)
    correct = _issue_planted_code(anon_client, db, victim)
    limit = settings.password_reset_max_attempts

    # 상한만큼 틀린 코드를 넣는다 — 전부 400 이어야 한다.
    for _ in range(limit):
        r = anon_client.post(
            CONFIRM_URL,
            json={
                "email": victim.email,
                "code": "000000",
                "newPassword": NEW_PASSWORD,
            },
        )
        assert r.status_code == 400

    # 상한을 넘긴 순간부터는 **맞는 코드조차** 통하면 안 된다(코드가 죽어야 한다).
    r = anon_client.post(
        CONFIRM_URL,
        json={
            "email": victim.email,
            "code": correct,
            "newPassword": NEW_PASSWORD,
        },
    )
    assert r.status_code != 204, (
        "상한을 넘긴 코드로 비밀번호가 바뀌었다 — 무차별 대입 방어가 뚫린다."
    )

    db.refresh(victim)
    assert verify_password(OLD_PASSWORD, victim.password_hash), "비밀번호가 실제로 바뀌어 버렸다."


# ---------------------------------------------------------------------------
# 공격 4 — 틀린 시도의 횟수 증가가 롤백돼서 무한 시도가 되는가
# ---------------------------------------------------------------------------


def test_공격_틀린_코드_시도횟수는_남는다(anon_client: TestClient, db: Session) -> None:
    """틀린 confirm 이 실패로 롤백되며 attempt_count 도 같이 되돌아가면 상한이 무의미해진다."""
    victim = _local_user(db)
    _issue_planted_code(anon_client, db, victim)

    for expected in range(1, 4):
        anon_client.post(
            CONFIRM_URL,
            json={
                "email": victim.email,
                "code": "999999",
                "newPassword": NEW_PASSWORD,
            },
        )
        row = _latest_code_row(db, victim)
        db.refresh(row)
        assert row.attempt_count == expected, (
            f"{expected}번째 틀린 시도 후 attempt_count={row.attempt_count} — "
            f"증가분이 롤백되면 무한히 찍을 수 있다."
        )


# ---------------------------------------------------------------------------
# 공격 5 — 이미 쓴 코드를 다시 쓸 수 있는가
# ---------------------------------------------------------------------------


def test_공격_쓴_코드_재사용(anon_client: TestClient, db: Session) -> None:
    victim = _local_user(db)
    code = _issue_planted_code(anon_client, db, victim)

    first = anon_client.post(
        CONFIRM_URL,
        json={
            "email": victim.email,
            "code": code,
            "newPassword": NEW_PASSWORD,
        },
    )
    assert first.status_code == 204  # 정상 1회 성공

    second = anon_client.post(
        CONFIRM_URL,
        json={
            "email": victim.email,
            "code": code,
            "newPassword": "another-pw-789",
        },
    )
    assert second.status_code != 204, (
        "같은 코드로 비밀번호를 두 번 바꿀 수 있다 — 코드 재사용 방어가 뚫린다."
    )


# ---------------------------------------------------------------------------
# 공격 6 — 한 계정에 발급된 코드를 다른 계정 이메일로 쓸 수 있는가
# ---------------------------------------------------------------------------


def test_공격_남의_코드로_비번변경(anon_client: TestClient, db: Session) -> None:
    """A 에게 온 코드를 B 이메일로 제출하면(같은 6자리 우연 일치 가정) 통하면 안 된다."""
    a = _local_user(db)
    b = _local_user(db)
    code = _issue_planted_code(anon_client, db, a)  # A 에게만 발급

    r = anon_client.post(
        CONFIRM_URL,
        json={
            "email": b.email,
            "code": code,
            "newPassword": NEW_PASSWORD,
        },
    )
    assert r.status_code != 204, (
        "다른 계정의 코드로 비밀번호가 바뀌었다 — 코드가 계정에 묶여 있지 않다."
    )

    db.refresh(b)
    assert verify_password(OLD_PASSWORD, b.password_hash)


# ---------------------------------------------------------------------------
# 공격 7 — verify 만 반복해서 정상 사용자의 코드를 죽일 수 있는가
# ---------------------------------------------------------------------------


def test_공격_verify_반복으로_코드_고갈(anon_client: TestClient, db: Session) -> None:
    """맞는 코드로 verify 를 여러 번 해도 코드가 소모되거나 시도횟수가 늘면 안 된다.

    verify 가 맞을 때도 카운트를 세면, 공격자가 아니라 정상 사용자가 재설정 한 번에
    시도 여러 번을 쓰게 된다(=오타 몇 번에 잠김).
    """
    victim = _local_user(db)
    code = _issue_planted_code(anon_client, db, victim)

    for _ in range(10):
        assert (
            anon_client.post(
                VERIFY_URL,
                json={
                    "email": victim.email,
                    "code": code,
                },
            ).status_code
            == 204
        )

    row = _latest_code_row(db, victim)
    db.refresh(row)
    assert row.used_at is None, "verify 가 코드를 소모했다."
    assert row.attempt_count == 0, "맞는 verify 가 시도횟수를 늘렸다."
