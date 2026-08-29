"""이메일 확인·로그아웃·회원 탈퇴 통합 테스트."""

import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models import User
from app.db.models.enums import AuthProvider


def _make_local_user(db: Session, email: str, password: str) -> User:
    user = User(
        id=uuid.uuid4(),
        nickname="탈퇴예정",
        email=email,
        auth_provider=AuthProvider.LOCAL,
        password_hash=hash_password(password),
    )
    db.add(user)
    db.flush()
    return user


# ---------------------------------------------------------------------------
# GET /auth/check-email
# ---------------------------------------------------------------------------


def test_없는_이메일은_available_true(client: TestClient) -> None:
    response = client.get("/api/v1/auth/check-email", params={"email": "free@example.com"})
    assert response.status_code == 200
    assert response.json() == {"available": True}


def test_가입된_이메일은_available_false(client: TestClient, db: Session) -> None:
    _make_local_user(db, "taken@example.com", "password123")
    response = client.get("/api/v1/auth/check-email", params={"email": "taken@example.com"})
    assert response.json() == {"available": False}


def test_탈퇴_이메일도_available_false(client: TestClient, db: Session) -> None:
    user = _make_local_user(db, "left@example.com", "password123")
    user.deleted_at = datetime.now(UTC)
    db.flush()
    response = client.get("/api/v1/auth/check-email", params={"email": "left@example.com"})
    assert response.json() == {"available": False}


def test_check_email_정규화하고_형식오류는_422(client: TestClient, db: Session) -> None:
    _make_local_user(db, "norm@example.com", "password123")
    # 대문자·공백을 보내도 정규화 후 같은 행을 찾는다.
    hit = client.get("/api/v1/auth/check-email", params={"email": "  NORM@Example.com "})
    assert hit.json() == {"available": False}

    bad = client.get("/api/v1/auth/check-email", params={"email": "not-an-email"})
    assert bad.status_code == 422


# ---------------------------------------------------------------------------
# POST /auth/logout
# ---------------------------------------------------------------------------


def test_로그아웃은_204(client: TestClient) -> None:
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 204
    assert response.content == b""


# ---------------------------------------------------------------------------
# DELETE /users/me
# ---------------------------------------------------------------------------


def test_회원탈퇴는_비밀번호_재확인_후_soft_delete(
    client: TestClient, db: Session, owner: User
) -> None:
    owner.auth_provider = AuthProvider.LOCAL
    owner.password_hash = hash_password("password123")
    db.flush()

    response = client.request("DELETE", "/api/v1/users/me", json={"password": "password123"})

    assert response.status_code == 204
    db.refresh(owner)
    assert owner.deleted_at is not None


def test_틀린_비밀번호_탈퇴는_401_이고_계정은_남는다(
    client: TestClient, db: Session, owner: User
) -> None:
    owner.auth_provider = AuthProvider.LOCAL
    owner.password_hash = hash_password("password123")
    db.flush()

    response = client.request("DELETE", "/api/v1/users/me", json={"password": "wrongpassword"})

    assert response.status_code == 401
    db.refresh(owner)
    assert owner.deleted_at is None
