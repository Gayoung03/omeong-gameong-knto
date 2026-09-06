"""Lane A 공격: 비밀번호 재설정 단계 간 '신원 뒤바꾸기'.

verify(단계1) 와 confirm(단계2) 사이에서 이메일(신원)을 바꿔치기하거나, 남의
코드를 자기 이메일에 붙이거나, verify 를 건너뛰고 confirm 으로 직행할 때
**대상 유저의 비밀번호를 바꿀 수 있는가**를 pytest 로 증명한다.

판정 규칙
- '막힘'은 정확한 상태코드(정상=204, 불일치/만료/사용=400, 상한초과=429)와 body 로 단언한다.
- 각 '막힘' 테스트에는 positive control(같은 경로가 정상 조건에서는 204)을 붙여
  껍데기가 아님을 증명한다.
- assert 메시지에 settings 객체를 직접 넣지 않는다 — 필요한 값은 int() 로 지역변수에 뽑는다.

이 파일은 소스/기존 테스트/conftest 를 건드리지 않는다. conftest 의 anon_client(실제
인증 경로)·db(트랜잭션 롤백) 픽스처만 재사용한다.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.db.models import PasswordResetCode, User
from app.db.models.enums import AuthProvider

REQUEST_URL = "/api/v1/auth/password-reset/request"
VERIFY_URL = "/api/v1/auth/password-reset/verify"
CONFIRM_URL = "/api/v1/auth/password-reset/confirm"

# HTTPException detail 문구(auth.py _raise_for_reset_result 와 정확히 일치해야 한다).
INVALID_DETAIL = "인증번호가 올바르지 않거나 만료되었습니다"
TOO_MANY_DETAIL = "입력 시도가 너무 많습니다. 코드를 다시 요청해 주세요"

A_PW = "alpha-original-pw-111"
B_PW = "bravo-original-pw-222"
A_CODE = "111111"
B_CODE = "222222"
NEW_PW = "attacker-new-pw-9999"
NEW_PW_2 = "control-new-pw-8888"


def _make_local_user(db: Session, nickname: str, password: str) -> User:
    user = User(
        id=uuid.uuid4(),
        nickname=nickname,
        email=f"{uuid.uuid4().hex}@example.com",
        password_hash=hash_password(password),
        auth_provider=AuthProvider.LOCAL,
    )
    db.add(user)
    db.flush()
    return user


@pytest.fixture
def user_a(db: Session) -> User:
    return _make_local_user(db, "유저A", A_PW)


@pytest.fixture
def user_b(db: Session) -> User:
    return _make_local_user(db, "유저B", B_PW)


def _latest_code_row(db: Session, user: User) -> PasswordResetCode | None:
    return db.scalar(
        select(PasswordResetCode)
        .where(PasswordResetCode.user_id == user.id)
        .order_by(PasswordResetCode.created_at.desc())
    )


def _issue_code_for(client: TestClient, db: Session, user: User, plaintext: str) -> str:
    """이 유저에게 코드를 발급받고, 그 평문을 `plaintext` 로 심는다(test_password_reset 기법).

    코드는 해시로만 저장돼 되읽을 수 없으므로, 발급된 행의 code_hash 를 우리가 아는
    평문의 해시로 덮어써 A/B 에게 서로 다른 알려진 코드를 준다.
    """
    resp = client.post(REQUEST_URL, json={"email": user.email})
    assert resp.status_code == 202
    row = _latest_code_row(db, user)
    assert row is not None, "발급 경로가 코드 행을 만들지 않았다"
    row.code_hash = hash_password(plaintext)
    db.flush()
    return plaintext


def _confirm(client: TestClient, email: str, code: str, new_password: str):
    return client.post(
        CONFIRM_URL, json={"email": email, "code": code, "newPassword": new_password}
    )


def _verify(client: TestClient, email: str, code: str):
    return client.post(VERIFY_URL, json={"email": email, "code": code})


# ---------------------------------------------------------------------------
# A-1: verify 를 A 로 통과시킨 사실이 confirm 의 B 에 전이되는가
# ---------------------------------------------------------------------------


def test_A1_verify를_A로_통과해도_confirm의_B에_전이되지_않는다(
    anon_client: TestClient, db: Session, user_a: User, user_b: User
) -> None:
    """verify(A) 성공이 confirm(B) 로 넘어가 B 비번을 바꾸면 완전한 계정 탈취."""
    a_code = _issue_code_for(anon_client, db, user_a, A_CODE)
    b_code = _issue_code_for(anon_client, db, user_b, B_CODE)

    # 전제 control: verify(A, A의 코드) 는 실제로 통과한다(204). verify 가 A 를
    # 진짜로 인증했음을 보장 — 이후 막힘이 'verify 실패' 때문이 아님을 못박는다.
    assert _verify(anon_client, user_a.email, a_code).status_code == 204

    # 공격: A 로 verify 를 통과한 직후, B 이메일 + A 의 코드로 확정 시도.
    attack = _confirm(anon_client, user_b.email, a_code, NEW_PW)

    assert attack.status_code == 400
    assert attack.json()["detail"] == INVALID_DETAIL

    # 대상(B)·A 둘 다 원래 비번 그대로.
    db.refresh(user_a)
    db.refresh(user_b)
    assert verify_password(B_PW, user_b.password_hash)
    assert verify_password(A_PW, user_a.password_hash)

    # positive control: 같은 confirm 엔드포인트가 B 자기 코드로는 204 로 성공 →
    # 위 400 이 껍데기가 아니라 '신원/코드 불일치' 때문임을 증명.
    control = _confirm(anon_client, user_b.email, b_code, NEW_PW_2)
    assert control.status_code == 204
    db.refresh(user_b)
    assert verify_password(NEW_PW_2, user_b.password_hash)


# ---------------------------------------------------------------------------
# A-2: 내 이메일에 남의 코드를 붙일 수 있는가
# ---------------------------------------------------------------------------


def test_A2_A이메일에_B에게_발급된_코드로는_바꿀_수_없다(
    anon_client: TestClient, db: Session, user_a: User, user_b: User
) -> None:
    """confirm 이 email 로 유저를 찾고 그 유저의 코드로만 대조하는지 확인."""
    a_code = _issue_code_for(anon_client, db, user_a, A_CODE)
    b_code = _issue_code_for(anon_client, db, user_b, B_CODE)

    # 공격: A 이메일 + B 의 코드.
    attack = _confirm(anon_client, user_a.email, b_code, NEW_PW)

    assert attack.status_code == 400
    assert attack.json()["detail"] == INVALID_DETAIL

    db.refresh(user_a)
    db.refresh(user_b)
    assert verify_password(A_PW, user_a.password_hash)  # A 그대로
    assert verify_password(B_PW, user_b.password_hash)  # B 그대로

    # positive control: A 이메일 + A 자기 코드는 204 → 경로가 정상 동작.
    control = _confirm(anon_client, user_a.email, a_code, NEW_PW_2)
    assert control.status_code == 204
    db.refresh(user_a)
    assert verify_password(NEW_PW_2, user_a.password_hash)


# ---------------------------------------------------------------------------
# A-3: verify 를 건너뛴 confirm 직행 — 되는가? 되면 위험한가?
# ---------------------------------------------------------------------------


def test_A3_verify_없이_confirm_직행이_된다(
    anon_client: TestClient, db: Session, user_a: User
) -> None:
    """verify 를 아예 안 부르고 confirm 만 호출해도 통한다(설계상 허용)."""
    a_code = _issue_code_for(anon_client, db, user_a, A_CODE)

    # verify 호출 없음.
    direct = _confirm(anon_client, user_a.email, a_code, NEW_PW)

    assert direct.status_code == 204
    db.refresh(user_a)
    assert verify_password(NEW_PW, user_a.password_hash)


def test_A3_confirm은_verify_생략시에도_코드를_스스로_재검증한다(
    anon_client: TestClient, db: Session, user_a: User
) -> None:
    """직행이 위험하지 않은 근거: confirm 이 자체적으로 코드를 대조한다.

    verify 를 건너뛰고 '틀린 코드'로 직행하면 막힌다(400) → confirm 이 verify
    통과 여부에 기대지 않고 스스로 검증한다는 증거.
    """
    a_code = _issue_code_for(anon_client, db, user_a, A_CODE)

    # 공격: verify 생략 + 틀린 코드 직행.
    wrong = _confirm(anon_client, user_a.email, "999999", NEW_PW)
    assert wrong.status_code == 400
    assert wrong.json()["detail"] == INVALID_DETAIL
    db.refresh(user_a)
    assert verify_password(A_PW, user_a.password_hash)  # 안 바뀜

    # positive control: 같은 직행 경로에 '맞는 코드'면 204(코드는 아직 살아 있다) →
    # 위 400 이 '틀린 코드' 때문이지 직행 자체가 막힌 게 아님을 증명.
    ok = _confirm(anon_client, user_a.email, a_code, NEW_PW_2)
    assert ok.status_code == 204
    db.refresh(user_a)
    assert verify_password(NEW_PW_2, user_a.password_hash)


# ---------------------------------------------------------------------------
# 변형 공격 (이 레인 안에서 떠오르는 것)
# ---------------------------------------------------------------------------


def test_변형_verify_단계도_신원별로_격리된다(
    anon_client: TestClient, db: Session, user_a: User, user_b: User
) -> None:
    """verify 자체도 email 로 유저를 찾아 그 유저 코드로만 대조하는지."""
    a_code = _issue_code_for(anon_client, db, user_a, A_CODE)
    b_code = _issue_code_for(anon_client, db, user_b, B_CODE)

    # 공격: B 이메일 + A 의 코드로 verify.
    attack = _verify(anon_client, user_b.email, a_code)
    assert attack.status_code == 400
    assert attack.json()["detail"] == INVALID_DETAIL

    # positive control: 각자 자기 코드는 204.
    assert _verify(anon_client, user_a.email, a_code).status_code == 204
    assert _verify(anon_client, user_b.email, b_code).status_code == 204


def test_변형_이메일_대소문자_공백은_같은_신원으로_정규화된다(
    anon_client: TestClient, db: Session, user_a: User
) -> None:
    """대소문자/공백 변형으로 '다른 신원'을 만들어 우회할 수 있나 → 없다.

    NormalizedEmail 이 소문자+trim 으로 같은 계정에 매핑하므로 신원 틈이 안 생긴다.
    (틈이 있었다면 confirm 이 정규화 전 문자열로 유저를 못 찾아 400 이 났을 것.)
    """
    a_code = _issue_code_for(anon_client, db, user_a, A_CODE)

    weird_email = f"  {user_a.email.upper()}  "
    resp = _confirm(anon_client, weird_email, a_code, NEW_PW)

    assert resp.status_code == 204  # 같은 A 계정으로 정규화되어 정상 처리
    db.refresh(user_a)
    assert verify_password(NEW_PW, user_a.password_hash)


def test_변형_없는_이메일에_유효코드를_붙여도_막힌다(
    anon_client: TestClient, db: Session, user_a: User
) -> None:
    """존재하지 않는 이메일 + (다른 유저의) 유효한 코드 조합."""
    a_code = _issue_code_for(anon_client, db, user_a, A_CODE)
    ghost_email = f"ghost-{uuid.uuid4().hex}@example.com"

    attack = _confirm(anon_client, ghost_email, a_code, NEW_PW)

    assert attack.status_code == 400
    assert attack.json()["detail"] == INVALID_DETAIL
    db.refresh(user_a)
    assert verify_password(A_PW, user_a.password_hash)  # A 는 건드려지지 않음

    # positive control: 그 코드는 진짜 주인(A)에게는 204 로 유효.
    control = _confirm(anon_client, user_a.email, a_code, NEW_PW_2)
    assert control.status_code == 204
    db.refresh(user_a)
    assert verify_password(NEW_PW_2, user_a.password_hash)


def test_변형_공격자가_피해자_코드의_시도횟수를_소진시켜_재설정을_막는다(
    anon_client: TestClient, db: Session, user_a: User
) -> None:
    """참고(availability): 이메일만 알면 남의 살아있는 코드를 '죽일' 수 있다.

    비번 탈취(integrity)는 아니고, 무차별 대입 방어(attempt 상한)의 부작용으로
    생기는 표적 DoS 다. confirm 이 대조 전에 attempt_count 를 올리므로, 공격자가
    틀린 코드를 상한만큼 던지면 피해자 자신의 '맞는 코드'가 429 로 죽는다.
    """
    max_attempts = int(settings.password_reset_max_attempts)
    a_code = _issue_code_for(anon_client, db, user_a, A_CODE)

    # 공격자는 코드값을 모른 채(이메일만 알고) 틀린 코드를 상한만큼 던진다.
    for _ in range(max_attempts):
        r = _confirm(anon_client, user_a.email, "000000", NEW_PW)
        assert r.status_code == 400

    # 이제 피해자의 '맞는 코드'조차 상한 초과로 죽어 있다(429).
    victim = _confirm(anon_client, user_a.email, a_code, NEW_PW)
    assert victim.status_code == 429
    assert victim.json()["detail"] == TOO_MANY_DETAIL

    # 비번은 안 바뀜 — 탈취가 아니라 재설정 불능(DoS)임을 확인.
    db.refresh(user_a)
    assert verify_password(A_PW, user_a.password_hash)
