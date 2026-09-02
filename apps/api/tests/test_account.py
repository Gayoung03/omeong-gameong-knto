"""이메일 확인·로그아웃·회원 탈퇴 통합 테스트."""

import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models import (
    ChatConversation,
    ChatMessage,
    User,
    UserSocialAccount,
    UserTravelPreference,
)
from app.db.models.enums import AuthProvider, MessageRole, TripPace
from app.integrations.social_auth.kakao import SocialAuthError, SocialProfile, get_kakao_client
from app.main import app


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


# ---------------------------------------------------------------------------
# 소셜 계정 탈퇴 — 제공처 재인증
# ---------------------------------------------------------------------------


class _FakeKakaoReauth:
    """verify_access_token 만 흉내내는 fake. provider_user_id 또는 에러를 주입."""

    def __init__(self, provider_user_id: str | None = None, error: Exception | None = None):
        self._provider_user_id = provider_user_id
        self._error = error

    def verify_access_token(self, access_token: str) -> SocialProfile:
        if self._error is not None:
            raise self._error
        return SocialProfile(
            provider="kakao",
            provider_user_id=self._provider_user_id or "kk-1",
            email=None,
            nickname="카카오",
            profile_image_url=None,
        )


def _make_kakao_owner(db: Session, owner: User, provider_user_id: str = "kk-1") -> None:
    owner.auth_provider = AuthProvider.KAKAO
    owner.password_hash = None
    db.add(
        UserSocialAccount(
            user_id=owner.id, provider=AuthProvider.KAKAO, provider_user_id=provider_user_id
        )
    )
    db.flush()


def test_소셜_계정_탈퇴는_제공처_재인증으로_204(
    client: TestClient, db: Session, owner: User
) -> None:
    _make_kakao_owner(db, owner, "kk-1")
    app.dependency_overrides[get_kakao_client] = lambda: _FakeKakaoReauth(provider_user_id="kk-1")

    response = client.request("DELETE", "/api/v1/users/me", json={"providerAccessToken": "tok"})

    assert response.status_code == 204
    db.refresh(owner)
    assert owner.deleted_at is not None


def test_소셜_탈퇴_토큰_없으면_401(client: TestClient, db: Session, owner: User) -> None:
    _make_kakao_owner(db, owner, "kk-1")
    app.dependency_overrides[get_kakao_client] = lambda: _FakeKakaoReauth(provider_user_id="kk-1")

    response = client.request("DELETE", "/api/v1/users/me", json={})

    assert response.status_code == 401
    db.refresh(owner)
    assert owner.deleted_at is None


def test_남의_소셜_토큰으로는_탈퇴_불가_401(client: TestClient, db: Session, owner: User) -> None:
    _make_kakao_owner(db, owner, "kk-1")
    # 토큰은 유효하지만 다른 계정(kk-other) 소유 → 거부.
    app.dependency_overrides[get_kakao_client] = lambda: _FakeKakaoReauth(
        provider_user_id="kk-other"
    )

    response = client.request("DELETE", "/api/v1/users/me", json={"providerAccessToken": "tok"})

    assert response.status_code == 401
    db.refresh(owner)
    assert owner.deleted_at is None


def test_소셜_토큰_무효면_401(client: TestClient, db: Session, owner: User) -> None:
    _make_kakao_owner(db, owner, "kk-1")
    app.dependency_overrides[get_kakao_client] = lambda: _FakeKakaoReauth(
        error=SocialAuthError("x")
    )

    response = client.request("DELETE", "/api/v1/users/me", json={"providerAccessToken": "bad"})

    assert response.status_code == 401
    db.refresh(owner)
    assert owner.deleted_at is None


def test_탈퇴하면_챗봇_대화만_즉시_지워진다(
    client: TestClient, db: Session, owner: User, stranger: User
) -> None:
    """users.md — 탈퇴 시 chat_conversations 물리 삭제. 다른 데이터·다른 사용자는 불변."""
    owner.auth_provider = AuthProvider.LOCAL
    owner.password_hash = hash_password("password123")
    mine = ChatConversation(id=uuid.uuid4(), user_id=owner.id, title="내 대화")
    yours = ChatConversation(id=uuid.uuid4(), user_id=stranger.id, title="남의 대화")
    db.add_all([mine, yours])
    db.flush()
    db.add(
        ChatMessage(
            id=uuid.uuid4(),
            conversation_id=mine.id,
            role=MessageRole.USER,
            content="우리 애 체중이 12kg인데 탈 수 있어?",
        )
    )
    preference = UserTravelPreference(user_id=owner.id, default_pace=TripPace.RELAXED)
    db.add(preference)
    db.flush()

    response = client.request("DELETE", "/api/v1/users/me", json={"password": "password123"})

    assert response.status_code == 204
    remaining = db.scalars(select(ChatConversation.id)).all()
    assert remaining == [yours.id]  # 내 대화·메시지만 사라진다 (메시지는 FK CASCADE)
    assert db.scalar(select(func.count(ChatMessage.id))) == 0
    db.refresh(owner)
    assert owner.deleted_at is not None  # soft delete 는 그대로
    assert db.get(UserTravelPreference, owner.id) is not None  # 다른 데이터 불변
