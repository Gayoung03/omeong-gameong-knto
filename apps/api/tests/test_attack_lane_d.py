"""공격 레인 D — 정보 노출 + 발송 남용 (보안 테스터 작성, 소스 무수정).

이 파일은 기능 검증이 아니라 **공격이 통하는지**를 증명한다. 각 테스트는
관측한 정확한 숫자(발송 통수·상태코드·body·타이밍)를 남겨 보고 근거로 쓴다.

안전장치는 전부 기존 conftest.py 가 잡는다:
- DB 는 TEST_DATABASE_URL 만 사용(없으면 스킵). 테스트 트랜잭션은 통째로 롤백.
- SMTP 설정을 비워 실제 메일이 나가지 않는다. 그 위에 send_email 자체를
  monkeypatch 로 가로채 **발송 대신 호출을 센다**(네트워크 변수도 제거).
"""

import statistics
import time
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


# ---------------------------------------------------------------------------
# 유저 생성 헬퍼 (tests/test_password_reset.py 의 패턴을 그대로 따른다)
# ---------------------------------------------------------------------------


def _make_local_user(db: Session) -> User:
    user = User(
        id=uuid.uuid4(),
        nickname="로컬피해자",
        email=f"{uuid.uuid4().hex}@example.com",
        password_hash=hash_password("old-password-123"),
        auth_provider=AuthProvider.LOCAL,
    )
    db.add(user)
    db.flush()
    return user


def _make_kakao_user(db: Session) -> User:
    """카카오(소셜) 계정 — password_hash=None. request_reset 의 소셜 분기 대상."""
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


def _count_sender(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    """send_email 을 가로채 (to, subject) 를 모으는 리스트를 돌려준다.

    password_reset 모듈이 `from app.services.email import send_email` 로 이름을
    자기 네임스페이스에 묶어 두므로, 그 모듈의 속성을 갈아끼우면 발송이 잡힌다.
    """
    sent: list[tuple[str, str]] = []
    monkeypatch.setattr(
        password_reset, "send_email", lambda to, subject, body: sent.append((to, subject))
    )
    return sent


# ---------------------------------------------------------------------------
# 공격 1 — V1 소셜 메일 폭탄 (실측·중요)
# ---------------------------------------------------------------------------


def test_v1_social_mail_bomb_capped_after_fix(
    anon_client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """[V1 회귀 가드] 소셜 계정 안내 메일도 시간당 발송 상한에 걸려야 한다.

    수정 전: `auth_provider != LOCAL` 분기가 상한 검사보다 위에 있었고, 소셜은
    PasswordResetCode 행을 안 만들어 발송을 셀 근거가 없어 상한이 통째로 우회됐다
    (요청 수만큼 안내 메일 발송 = 발신 도메인 평판 손상).

    수정 후: 발송마다 `password_reset_requests` 행을 남기고 상한 검사를 소셜 분기
    위로 올려, 소셜·local 모두 hourly_limit 통에서 멈춘다. 비교군으로 local 도 난사한다.
    """
    hourly_limit = int(settings.password_reset_hourly_limit)
    attempts = hourly_limit * 4

    sent = _count_sender(monkeypatch)

    # --- 소셜(KAKAO) 계정 난사 ---
    social = _make_kakao_user(db)
    for _ in range(attempts):
        response = anon_client.post(REQUEST_URL, json={"email": social.email})
        assert response.status_code == 202
    social_sent = len(sent)

    # --- 동일 횟수로 local 계정 난사(비교군) ---
    sent.clear()
    local = _make_local_user(db)
    for _ in range(attempts):
        response = anon_client.post(REQUEST_URL, json={"email": local.email})
        assert response.status_code == 202
    local_sent = len(sent)

    print(
        f"\n[REPORT V1] hourly_limit={hourly_limit} attempts={attempts} "
        f"social_sent={social_sent} local_sent={local_sent}"
    )

    # [수정 후 회귀 가드] 소셜도 발송 기록(password_reset_requests) 행으로 상한이
    # 걸린다. 소셜·local 모두 hourly_limit 통에서 멈춰야 한다. (수정 전엔 소셜이
    # attempts 통 그대로 나가 social_sent == local_sent*4 였다 — 그 뚫림이 막혔다.)
    assert social_sent == hourly_limit, f"소셜 발송이 상한을 넘음: {social_sent}"
    assert local_sent == hourly_limit, f"local 발송이 상한을 넘음: {local_sent}"


# ---------------------------------------------------------------------------
# 공격 2 — 열거(#6): 응답 내용으로 가입 여부를 알 수 있나
# ---------------------------------------------------------------------------


def test_enum_registered_vs_unregistered_response_identical(
    anon_client: TestClient, db: Session
) -> None:
    """가입 이메일 vs 미가입 이메일 → 상태코드·body 가 완전히 같아야 막힘."""
    local = _make_local_user(db)
    registered = anon_client.post(REQUEST_URL, json={"email": local.email})
    unregistered = anon_client.post(REQUEST_URL, json={"email": f"{uuid.uuid4().hex}@example.com"})

    print(
        f"\n[REPORT #6] registered=({registered.status_code}, {registered.content!r}) "
        f"unregistered=({unregistered.status_code}, {unregistered.content!r})"
    )

    assert registered.status_code == unregistered.status_code == 202
    assert registered.content == unregistered.content == b""


def test_enum_social_vs_unregistered_response_identical(
    anon_client: TestClient, db: Session
) -> None:
    """추가 변형 — 소셜 계정도 미가입과 동일 응답이어야 소셜 여부가 새지 않는다."""
    social = _make_kakao_user(db)
    social_resp = anon_client.post(REQUEST_URL, json={"email": social.email})
    unregistered = anon_client.post(REQUEST_URL, json={"email": f"{uuid.uuid4().hex}@example.com"})

    print(
        f"\n[REPORT #6-social] social=({social_resp.status_code}, {social_resp.content!r}) "
        f"unregistered=({unregistered.status_code}, {unregistered.content!r})"
    )

    assert social_resp.status_code == unregistered.status_code == 202
    assert social_resp.content == unregistered.content == b""


def test_enum_email_case_variants_response_identical(
    anon_client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """추가 변형 — 대소문자 이메일 변형 열거.

    이메일은 소문자+trim 으로 정규화되므로 UPPER/혼합/앞뒤 공백이 모두 같은 계정을
    찾아 같은 응답을 낸다(대소문자로 존재 여부를 가려낼 수 없다). 정규화로 같은
    계정을 찾는지도 발송 카운트로 함께 확인한다.
    """
    local = _make_local_user(db)
    sent = _count_sender(monkeypatch)

    variants = [
        local.email,
        local.email.upper(),
        local.email.swapcase(),
        f"  {local.email.upper()}  ",
    ]
    responses = [anon_client.post(REQUEST_URL, json={"email": v}) for v in variants]

    codes = {r.status_code for r in responses}
    bodies = {r.content for r in responses}
    print(
        f"\n[REPORT case-variant] status_codes={codes} bodies={bodies} "
        f"sent_to_same_account={len(sent)}"
    )

    # 모든 변형이 같은 202·같은 빈 body.
    assert codes == {202}
    assert bodies == {b""}
    # 4번 다 정규화되어 같은 계정을 찾아 발송됐다(대소문자가 계정을 가르지 않는다).
    assert len(sent) == len(variants)


# ---------------------------------------------------------------------------
# 공격 3 — 열거(#7): 응답 시간 차 (참고 등급)
# ---------------------------------------------------------------------------


def test_timing_registered_vs_unregistered_reference(
    anon_client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """가입 vs 미가입 응답 시간 분포 비교 — **참고 등급**.

    request 는 발급·발송을 BackgroundTasks 로 빼서, 설계상 응답경로 시간이 계정
    유무와 무관하다(엔드포인트 본체는 add_task + 202 뿐).

    주의(해석의 한계): TestClient 는 응답 뒤 백그라운드 태스크를 **동기로** 실행해
    그 시간이 벽시계에 포함된다. 그래서 여기서 재는 값은 순수 응답경로가 아니라
    "응답 + 백그라운드"다. 가입 local 은 백그라운드에서 argon2 해싱까지 도니
    미가입보다 느리게 찍힐 수 있는데, 이는 **하니스 아티팩트**이지 운영에서의
    타이밍 오라클이 아니다(운영은 202 를 먼저 돌려주고 그 뒤 비동기로 해싱).
    그래서 이 테스트는 수치만 남기고 통과/실패를 시간차로 가르지 않는다.
    """
    _count_sender(monkeypatch)  # SMTP 시도 변수 제거
    local = _make_local_user(db)

    def _elapsed(email: str) -> float:
        start = time.perf_counter()
        response = anon_client.post(REQUEST_URL, json={"email": email})
        dt = time.perf_counter() - start
        assert response.status_code == 202
        return dt

    # 워밍업(첫 argon2/커넥션 비용이 중앙값을 흔들지 않게).
    for _ in range(3):
        _elapsed(local.email)
        _elapsed(f"{uuid.uuid4().hex}@example.com")

    n = 30
    registered = sorted(_elapsed(local.email) for _ in range(n))
    unregistered = sorted(_elapsed(f"{uuid.uuid4().hex}@example.com") for _ in range(n))

    reg_med = statistics.median(registered) * 1000
    unreg_med = statistics.median(unregistered) * 1000
    print(
        f"\n[REPORT #7 timing ms, n={n}] registered_median={reg_med:.2f} "
        f"unregistered_median={unreg_med:.2f} "
        f"reg_min={registered[0] * 1000:.2f} unreg_min={unregistered[0] * 1000:.2f}"
    )

    # 참고 등급: 수치만 확보한다. 시간차로 통과/실패를 가르지 않는다(통계적으로
    # 흔들리고, TestClient 백그라운드 동기 실행 탓에 차이가 나도 운영 오라클이 아님).
    assert reg_med > 0 and unreg_med > 0
