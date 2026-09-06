"""V1 수정 검증 — 소셜 메일 폭탄 상한 + 우회 변형 공격.

수정: `password_reset_requests` 테이블에 발송마다 한 행을 남기고, 시간당 상한을
그 행 수로 센다(로컬·소셜 공통). 이 파일은 (1) 소셜도 상한에 걸리는지, (2) 상한을
우회하는 변형(이메일 대소문자/공백, 소셜·로컬 섞기, 계정별 독립)이 통하는지 확인한다.

실행:
    TEST_DATABASE_URL='postgresql+psycopg://omeong:omeong@localhost:5432/omeong_test_d' \
        uv run pytest tests/test_v1_fix.py -v
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.db.models import User
from app.db.models.enums import AuthProvider
from app.services import password_reset

REQUEST_URL = "/api/v1/auth/password-reset/request"


def _count_sender(monkeypatch: pytest.MonkeyPatch) -> list[tuple]:
    sent: list[tuple] = []
    monkeypatch.setattr(
        password_reset, "send_email", lambda to, subject, body: sent.append((to, subject))
    )
    return sent


def _kakao(db: Session) -> User:
    u = User(
        id=uuid.uuid4(),
        nickname="소셜",
        email=f"{uuid.uuid4().hex}@example.com",
        password_hash=None,
        auth_provider=AuthProvider.KAKAO,
        provider_user_id=uuid.uuid4().hex,
    )
    db.add(u)
    db.flush()
    return u


def _local(db: Session) -> User:
    u = User(
        id=uuid.uuid4(),
        nickname="로컬",
        email=f"{uuid.uuid4().hex}@example.com",
        password_hash=hash_password("pw-12345678"),
        auth_provider=AuthProvider.LOCAL,
    )
    db.add(u)
    db.flush()
    return u


def test_소셜_안내메일도_상한에_걸린다(
    anon_client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    limit = int(settings.password_reset_hourly_limit)
    sent = _count_sender(monkeypatch)
    u = _kakao(db)
    for _ in range(limit * 4):
        assert anon_client.post(REQUEST_URL, json={"email": u.email}).status_code == 202
    assert len(sent) == limit, f"소셜 발송이 상한을 넘음: {len(sent)}"


def test_이메일_대소문자_공백_변형으로_상한_우회_불가(
    anon_client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """같은 이메일의 대소문자/공백 변형으로 카운터를 우회하려는 시도.

    카운터가 원본 문자열로 키를 잡으면 변형마다 별개로 세어 우회된다. 실제로는
    NormalizedEmail(소문자+trim) 로 같은 계정을 찾고 카운터는 user_id 기준이라,
    변형을 아무리 섞어도 한 계정 상한(limit)에서 멈춰야 한다.
    """
    limit = int(settings.password_reset_hourly_limit)
    sent = _count_sender(monkeypatch)
    u = _kakao(db)
    base = u.email
    variants = [base, base.upper(), f"  {base}  ", base.swapcase(), f"{base.upper()} "]

    # 각 변형으로 limit 번씩 = limit*5 회 난사 — 우회되면 발송이 limit 을 크게 넘는다.
    for _ in range(limit):
        for v in variants:
            assert anon_client.post(REQUEST_URL, json={"email": v}).status_code == 202

    assert len(sent) == limit, (
        f"대소문자/공백 변형으로 상한이 우회됨: {len(sent)}통 나감(상한 {limit})"
    )


def test_소셜_로컬_섞어_요청해도_각자_상한(
    anon_client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """소셜·로컬 계정을 번갈아 난사해도 카운터가 계정별로 독립이라 서로 안 섞인다."""
    limit = int(settings.password_reset_hourly_limit)
    sent = _count_sender(monkeypatch)
    social = _kakao(db)
    local = _local(db)

    for _ in range(limit * 3):
        anon_client.post(REQUEST_URL, json={"email": social.email})
        anon_client.post(REQUEST_URL, json={"email": local.email})

    social_sent = sum(1 for to, _ in sent if to == social.email)
    local_sent = sum(1 for to, _ in sent if to == local.email)
    assert social_sent == limit, f"소셜 {social_sent}"
    assert local_sent == limit, f"로컬 {local_sent}"


def test_상한_카운터는_계정별로_독립(
    anon_client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """한 소셜 계정이 상한에 걸려도 다른 계정은 영향받지 않는다(과잉 차단 아님)."""
    limit = int(settings.password_reset_hourly_limit)
    sent = _count_sender(monkeypatch)
    a = _kakao(db)
    b = _kakao(db)

    for _ in range(limit * 2):  # a 를 상한까지 소진
        anon_client.post(REQUEST_URL, json={"email": a.email})
    a_sent = len(sent)
    assert a_sent == limit

    sent.clear()
    anon_client.post(REQUEST_URL, json={"email": b.email})  # b 는 여전히 발송돼야
    assert len(sent) == 1, "다른 계정까지 막혔다 — 과잉 차단"
