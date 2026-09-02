"""비밀번호 재설정 통합 테스트.

각 테스트는 "이걸 안 막으면 무슨 일이 나는가"를 이름에 적었다. 기능이 도는지가
아니라 **구멍이 막혀 있는지**를 확인하는 것이 이 파일의 목적이다.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_refresh_token, hash_password, verify_password
from app.db.models import PasswordResetCode, User
from app.db.models.enums import AuthProvider

REQUEST_URL = "/api/v1/auth/password-reset/request"
CONFIRM_URL = "/api/v1/auth/password-reset/confirm"

OLD_PASSWORD = "old-password-123"
NEW_PASSWORD = "new-password-456"


@pytest.fixture
def local_user(db: Session) -> User:
    """이메일로 가입한 살아 있는 계정."""
    user = User(
        id=uuid.uuid4(),
        nickname="재설정테스트",
        email=f"{uuid.uuid4().hex}@example.com",
        password_hash=hash_password(OLD_PASSWORD),
        auth_provider=AuthProvider.LOCAL,
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


def _issue_code(client: TestClient, db: Session, user: User) -> str:
    """코드를 발급받고, 그 평문을 알아낸다.

    코드는 해시로만 저장되므로 되읽을 수 없다. 000000~999999 를 대조하는 대신
    **테스트가 코드를 직접 심는다** — 발급 경로는 다른 테스트가 확인한다.
    """
    client.post(REQUEST_URL, json={"email": user.email})
    row = _latest_code_row(db, user)
    assert row is not None
    code = "123456"
    row.code_hash = hash_password(code)
    db.flush()
    return code


# ---------------------------------------------------------------------------
# 발급 — 가입 여부가 새지 않아야 한다
# ---------------------------------------------------------------------------


def test_없는_이메일도_가입된_이메일과_똑같은_202를_준다(
    anon_client: TestClient, local_user: User
) -> None:
    """응답이 다르면 그것만으로 가입자 목록을 훑을 수 있다."""
    있음 = anon_client.post(REQUEST_URL, json={"email": local_user.email})
    없음 = anon_client.post(REQUEST_URL, json={"email": "nobody-here@example.com"})

    assert 있음.status_code == 없음.status_code == 202
    assert 있음.content == 없음.content


def test_발급하면_코드가_해시로만_저장된다(
    anon_client: TestClient, db: Session, local_user: User
) -> None:
    """DB 가 유출돼도 코드가 평문으로 새면 안 된다."""
    anon_client.post(REQUEST_URL, json={"email": local_user.email})

    row = _latest_code_row(db, local_user)
    assert row is not None
    assert row.used_at is None
    assert row.attempt_count == 0
    assert row.expires_at > datetime.now(UTC)
    # argon2 해시는 $argon2 로 시작한다 — 6자리 숫자가 그대로 들어가 있지 않다.
    assert row.code_hash.startswith("$argon2")


def test_새_코드를_받으면_이전_코드는_폐기된다(
    anon_client: TestClient, db: Session, local_user: User
) -> None:
    """살아 있는 코드가 여러 개면 맞춰볼 수 있는 조합이 그만큼 늘어난다."""
    anon_client.post(REQUEST_URL, json={"email": local_user.email})
    first = _latest_code_row(db, local_user)
    assert first is not None

    anon_client.post(REQUEST_URL, json={"email": local_user.email})
    db.refresh(first)

    assert first.used_at is not None
    살아있는_코드 = db.scalars(
        select(PasswordResetCode).where(
            PasswordResetCode.user_id == local_user.id, PasswordResetCode.used_at.is_(None)
        )
    ).all()
    assert len(살아있는_코드) == 1


def test_소셜_계정에는_코드를_발급하지_않는다(anon_client: TestClient, db: Session) -> None:
    """비밀번호를 만들어 주면 원래 없던 로그인 경로가 새로 생긴다."""
    social = User(
        id=uuid.uuid4(),
        nickname="카카오사용자",
        email=f"{uuid.uuid4().hex}@example.com",
        password_hash=None,
        auth_provider=AuthProvider.KAKAO,
        provider_user_id=uuid.uuid4().hex,
    )
    db.add(social)
    db.flush()

    response = anon_client.post(REQUEST_URL, json={"email": social.email})

    # 응답은 local 계정과 동일하지만 코드는 만들어지지 않는다.
    assert response.status_code == 202
    assert _latest_code_row(db, social) is None


def test_탈퇴한_계정에는_코드를_발급하지_않는다(
    anon_client: TestClient, db: Session, local_user: User
) -> None:
    """탈퇴 계정이 재설정으로 되살아나면 안 된다."""
    local_user.deleted_at = datetime.now(UTC)
    db.flush()

    response = anon_client.post(REQUEST_URL, json={"email": local_user.email})

    assert response.status_code == 202
    assert _latest_code_row(db, local_user) is None


def test_시간당_상한을_넘으면_더_발급하지_않는다(
    anon_client: TestClient, db: Session, local_user: User
) -> None:
    """상한이 없으면 남의 메일함에 코드 메일을 무한히 쏟아부을 수 있다."""
    for _ in range(settings.password_reset_hourly_limit):
        anon_client.post(REQUEST_URL, json={"email": local_user.email})
    발급_수 = len(
        db.scalars(
            select(PasswordResetCode).where(PasswordResetCode.user_id == local_user.id)
        ).all()
    )

    response = anon_client.post(REQUEST_URL, json={"email": local_user.email})

    # 상한을 넘겨도 응답은 같고(가입 여부가 새지 않게), 행만 늘지 않는다.
    assert response.status_code == 202
    이후_발급_수 = len(
        db.scalars(
            select(PasswordResetCode).where(PasswordResetCode.user_id == local_user.id)
        ).all()
    )
    assert 이후_발급_수 == 발급_수 == settings.password_reset_hourly_limit


def test_이메일_대소문자가_달라도_같은_계정을_찾는다(
    anon_client: TestClient, db: Session, local_user: User
) -> None:
    """정규화를 안 하면 '가입은 됐는데 재설정이 안 되는' 계정이 생긴다."""
    anon_client.post(REQUEST_URL, json={"email": local_user.email.upper()})

    assert _latest_code_row(db, local_user) is not None


# ---------------------------------------------------------------------------
# 확인 — 무차별 대입·재사용이 막혀야 한다
# ---------------------------------------------------------------------------


def test_맞는_코드는_비밀번호를_바꾼다(
    anon_client: TestClient, db: Session, local_user: User
) -> None:
    code = _issue_code(anon_client, db, local_user)

    response = anon_client.post(
        CONFIRM_URL,
        json={"email": local_user.email, "code": code, "newPassword": NEW_PASSWORD},
    )

    assert response.status_code == 204
    db.refresh(local_user)
    assert verify_password(NEW_PASSWORD, local_user.password_hash)
    assert not verify_password(OLD_PASSWORD, local_user.password_hash)
    assert local_user.password_changed_at is not None


def test_틀린_코드는_시도_횟수를_남긴다(
    anon_client: TestClient, db: Session, local_user: User
) -> None:
    """에러로 빠져나가며 카운터까지 롤백되면 횟수 제한이 통째로 무력해진다."""
    _issue_code(anon_client, db, local_user)

    response = anon_client.post(
        CONFIRM_URL,
        json={"email": local_user.email, "code": "999999", "newPassword": NEW_PASSWORD},
    )

    assert response.status_code == 400
    row = _latest_code_row(db, local_user)
    assert row is not None
    db.refresh(row)
    assert row.attempt_count == 1


def test_시도_횟수를_넘기면_코드가_죽는다(
    anon_client: TestClient, db: Session, local_user: User
) -> None:
    """6자리는 100만 조합뿐이라 무한히 찔러보게 두면 뚫린다."""
    code = _issue_code(anon_client, db, local_user)

    for _ in range(settings.password_reset_max_attempts):
        anon_client.post(
            CONFIRM_URL,
            json={"email": local_user.email, "code": "999999", "newPassword": NEW_PASSWORD},
        )

    # 상한을 넘긴 뒤에는 **맞는 코드를 넣어도** 통하지 않는다.
    response = anon_client.post(
        CONFIRM_URL,
        json={"email": local_user.email, "code": code, "newPassword": NEW_PASSWORD},
    )

    assert response.status_code == 429
    db.refresh(local_user)
    assert verify_password(OLD_PASSWORD, local_user.password_hash)


def test_한_번_쓴_코드는_다시_쓸_수_없다(
    anon_client: TestClient, db: Session, local_user: User
) -> None:
    code = _issue_code(anon_client, db, local_user)
    body = {"email": local_user.email, "code": code, "newPassword": NEW_PASSWORD}
    assert anon_client.post(CONFIRM_URL, json=body).status_code == 204

    두번째 = anon_client.post(CONFIRM_URL, json=body)

    assert 두번째.status_code == 400


def test_만료된_코드는_통하지_않는다(
    anon_client: TestClient, db: Session, local_user: User
) -> None:
    """메일함이 나중에 털려도 지난 코드로는 못 바꾸게 한다."""
    code = _issue_code(anon_client, db, local_user)
    row = _latest_code_row(db, local_user)
    assert row is not None
    row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db.flush()

    response = anon_client.post(
        CONFIRM_URL,
        json={"email": local_user.email, "code": code, "newPassword": NEW_PASSWORD},
    )

    assert response.status_code == 400


def test_코드_없이_확인만_호출하면_거부한다(anon_client: TestClient, local_user: User) -> None:
    response = anon_client.post(
        CONFIRM_URL,
        json={"email": local_user.email, "code": "123456", "newPassword": NEW_PASSWORD},
    )

    assert response.status_code == 400


def test_여섯자리가_아닌_코드는_대조하기_전에_막는다(
    anon_client: TestClient, local_user: User
) -> None:
    response = anon_client.post(
        CONFIRM_URL,
        json={"email": local_user.email, "code": "12-34-56", "newPassword": NEW_PASSWORD},
    )

    assert response.status_code == 422


def test_새_비밀번호도_가입과_같은_길이_규칙을_받는다(
    anon_client: TestClient, local_user: User
) -> None:
    """여기만 느슨하면 재설정이 비밀번호 규칙의 우회로가 된다."""
    response = anon_client.post(
        CONFIRM_URL,
        json={"email": local_user.email, "code": "123456", "newPassword": "짧음"},
    )

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# 비밀번호를 바꾸면 기존 세션이 끊겨야 한다
# ---------------------------------------------------------------------------


def test_비밀번호를_바꾸면_이전_refresh_token_이_무효가_된다(
    anon_client: TestClient, db: Session, local_user: User
) -> None:
    """이게 없으면 계정을 되찾아 비밀번호를 바꿔도 공격자가 14일 더 버틴다."""
    stolen = create_refresh_token(local_user.id)
    assert (
        anon_client.post("/api/v1/auth/refresh", json={"refreshToken": stolen}).status_code == 200
    )

    code = _issue_code(anon_client, db, local_user)
    anon_client.post(
        CONFIRM_URL,
        json={"email": local_user.email, "code": code, "newPassword": NEW_PASSWORD},
    )

    이후 = anon_client.post("/api/v1/auth/refresh", json={"refreshToken": stolen})
    assert 이후.status_code == 401


def test_비밀번호를_바꾸면_이전_access_token_도_무효가_된다(
    anon_client: TestClient, db: Session, local_user: User
) -> None:
    from app.core.security import create_access_token

    stolen = create_access_token(local_user.id)
    headers = {"Authorization": f"Bearer {stolen}"}
    assert anon_client.get("/api/v1/users/me", headers=headers).status_code == 200

    code = _issue_code(anon_client, db, local_user)
    anon_client.post(
        CONFIRM_URL,
        json={"email": local_user.email, "code": code, "newPassword": NEW_PASSWORD},
    )

    assert anon_client.get("/api/v1/users/me", headers=headers).status_code == 401


def test_새_비밀번호로는_바로_로그인된다(
    anon_client: TestClient, db: Session, local_user: User
) -> None:
    code = _issue_code(anon_client, db, local_user)
    anon_client.post(
        CONFIRM_URL,
        json={"email": local_user.email, "code": code, "newPassword": NEW_PASSWORD},
    )

    response = anon_client.post(
        "/api/v1/auth/login", json={"email": local_user.email, "password": NEW_PASSWORD}
    )

    assert response.status_code == 200
    assert response.json()["accessToken"]
