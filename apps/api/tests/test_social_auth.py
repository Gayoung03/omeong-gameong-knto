"""카카오 소셜 로그인 통합 테스트 (실 카카오 호출 없이 verifier fake 로).

auth.md 소셜 절의 판정 표(로그인·linkRequired·새 계정·탈퇴 4종)와 선점 가입 공격
차단, 교환 코드 1회성·만료, state·returnUrl 검증을 1:1로 확인한다.
"""

import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import encode_token, hash_password
from app.db.models import User, UserSocialAccount
from app.db.models.enums import AuthProvider
from app.integrations.social_auth.kakao import (
    SocialAuthError,
    SocialProfile,
    SocialProviderUnavailable,
    get_kakao_client,
)
from app.main import app

_AUTHORIZE = "/api/v1/auth/kakao/authorize"
_CALLBACK = "/api/v1/auth/kakao/callback"
_EXCHANGE = "/api/v1/auth/social/exchange"
_COMPLETE = "/api/v1/auth/social/complete"


class _FakeKakao:
    def __init__(self, profile: SocialProfile | None = None, error: Exception | None = None):
        self._profile = profile
        self._error = error

    def authorize_url(self, state: str, redirect_uri: str) -> str:
        return f"https://kauth.kakao.com/oauth/authorize?state={state}"

    def fetch_profile(self, code: str, redirect_uri: str) -> SocialProfile:
        if self._error is not None:
            raise self._error
        return self._profile


def _use_fake(profile: SocialProfile | None = None, error: Exception | None = None) -> None:
    app.dependency_overrides[get_kakao_client] = lambda: _FakeKakao(profile=profile, error=error)


def _profile(kakao_id: str = "kakao-1", email: str | None = None) -> SocialProfile:
    return SocialProfile(
        provider="kakao",
        provider_user_id=kakao_id,
        email=email,
        nickname="카카오사용자",
        profile_image_url="https://cdn.kakao/x.jpg",
    )


def _state(return_url: str = "exp://demo/cb") -> str:
    return encode_token({"returnUrl": return_url}, "oauth_state", timedelta(minutes=10))


def _exchange_code(profile: SocialProfile, ttl: timedelta = timedelta(seconds=60)) -> str:
    claims = {
        "provider": profile.provider,
        "puid": profile.provider_user_id,
        "email": profile.email,
        "nickname": profile.nickname,
        "image": profile.profile_image_url,
    }
    return encode_token(claims, "exchange", ttl)


def _callback_to_code(client: TestClient, profile: SocialProfile) -> str:
    _use_fake(profile=profile)
    response = client.get(
        _CALLBACK, params={"code": "authcode", "state": _state()}, follow_redirects=False
    )
    assert response.status_code == 302
    return parse_qs(urlsplit(response.headers["location"]).query)["code"][0]


def _make_local(
    db: Session, email: str, password: str = "password123", deleted: bool = False
) -> User:
    user = User(
        id=uuid.uuid4(),
        nickname="로컬",
        email=email,
        auth_provider=AuthProvider.LOCAL,
        password_hash=hash_password(password),
    )
    if deleted:
        user.deleted_at = datetime.now(UTC)
    db.add(user)
    db.flush()
    return user


# ---------------------------------------------------------------------------
# authorize / callback
# ---------------------------------------------------------------------------


def test_authorize는_카카오로_302하고_state를_싣는다(client: TestClient) -> None:
    _use_fake()
    response = client.get(_AUTHORIZE, params={"returnUrl": "exp://demo"}, follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"].startswith("https://kauth.kakao.com/oauth/authorize")
    assert "state=" in response.headers["location"]


def test_지원하지_않는_provider는_422(client: TestClient) -> None:
    response = client.get(
        "/api/v1/auth/google/authorize", params={"returnUrl": "exp://demo"}, follow_redirects=False
    )
    assert response.status_code == 422


def test_허용목록_밖_returnUrl은_422(client: TestClient) -> None:
    response = client.get(
        _AUTHORIZE, params={"returnUrl": "https://evil.com/steal"}, follow_redirects=False
    )
    assert response.status_code == 422


def test_state_불일치는_422(client: TestClient) -> None:
    _use_fake(profile=_profile())
    response = client.get(
        _CALLBACK, params={"code": "x", "state": "not-a-valid-state"}, follow_redirects=False
    )
    assert response.status_code == 422


def test_카카오_인증_실패는_401_제공처_불능은_502(client: TestClient) -> None:
    _use_fake(error=SocialAuthError("bad code"))
    unauthorized = client.get(
        _CALLBACK, params={"code": "x", "state": _state()}, follow_redirects=False
    )
    assert unauthorized.status_code == 401

    _use_fake(error=SocialProviderUnavailable("down"))
    bad_gateway = client.get(
        _CALLBACK, params={"code": "x", "state": _state()}, follow_redirects=False
    )
    assert bad_gateway.status_code == 502


# ---------------------------------------------------------------------------
# exchange — 판정 4종
# ---------------------------------------------------------------------------


def test_신규_소셜_가입(client: TestClient, db: Session) -> None:
    code = _callback_to_code(client, _profile(kakao_id="new-1", email=None))
    response = client.post(_EXCHANGE, json={"code": code})

    assert response.status_code == 200
    body = response.json()
    assert body["isNewUser"] is True
    assert body["accessToken"] and body["refreshToken"]
    assert body["user"]["authProvider"] == "kakao"
    assert body["user"]["email"] is None

    account = db.scalar(
        select(UserSocialAccount).where(UserSocialAccount.provider_user_id == "new-1")
    )
    assert account is not None


def test_재로그인은_같은_계정_isNewUser_false(client: TestClient) -> None:
    profile = _profile(kakao_id="repeat-1")
    first = client.post(_EXCHANGE, json={"code": _callback_to_code(client, profile)}).json()
    second = client.post(_EXCHANGE, json={"code": _callback_to_code(client, profile)}).json()

    assert first["isNewUser"] is True
    assert second["isNewUser"] is False
    assert first["user"]["id"] == second["user"]["id"]


def test_미검증_이메일은_linkRequired_미발동_새계정(client: TestClient, db: Session) -> None:
    # 같은 이메일의 활성 local 계정이 있어도, 프로필 이메일이 없으면(미검증) 연동 제안 없음.
    _make_local(db, "verified-owner@example.com")
    code = _callback_to_code(client, _profile(kakao_id="unverified-1", email=None))
    body = client.post(_EXCHANGE, json={"code": code}).json()
    assert body.get("linkRequired") is None
    assert body["isNewUser"] is True


def test_탈퇴_이메일_일치는_새계정_email_null(client: TestClient, db: Session) -> None:
    _make_local(db, "left@example.com", deleted=True)
    code = _callback_to_code(client, _profile(kakao_id="afterleave-1", email="left@example.com"))
    body = client.post(_EXCHANGE, json={"code": code}).json()
    assert body["isNewUser"] is True
    assert body["user"]["email"] is None


def test_탈퇴_소셜계정_재로그인은_401(client: TestClient, db: Session) -> None:
    # (provider, id) 가 탈퇴 사용자 소유면 401.
    user = _make_local(db, "ghost@example.com", deleted=True)
    db.add(
        UserSocialAccount(
            user_id=user.id, provider=AuthProvider.KAKAO, provider_user_id="ghost-1"
        )
    )
    db.flush()
    code = _callback_to_code(client, _profile(kakao_id="ghost-1"))
    response = client.post(_EXCHANGE, json={"code": code})
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# 교환 코드 1회성·만료
# ---------------------------------------------------------------------------


def test_교환_코드_재사용은_401(client: TestClient) -> None:
    code = _callback_to_code(client, _profile(kakao_id="once-1"))
    assert client.post(_EXCHANGE, json={"code": code}).status_code == 200
    assert client.post(_EXCHANGE, json={"code": code}).status_code == 401


def test_만료된_교환_코드는_401(client: TestClient) -> None:
    expired = _exchange_code(_profile(kakao_id="expired-1"), ttl=timedelta(seconds=-120))
    assert client.post(_EXCHANGE, json={"code": expired}).status_code == 401


def test_위조_교환_코드는_401(client: TestClient) -> None:
    assert client.post(_EXCHANGE, json={"code": "not.a.jwt"}).status_code == 401


# ---------------------------------------------------------------------------
# linkRequired → complete (link / separate) · 선점 가입 공격
# ---------------------------------------------------------------------------


def test_linkRequired_후_link_성공(client: TestClient, db: Session) -> None:
    _make_local(db, "owner@example.com", password="password123")
    exchange = client.post(
        _EXCHANGE, json={"code": _callback_to_code(client, _profile("link-1", "owner@example.com"))}
    ).json()

    assert exchange["linkRequired"] is True
    assert exchange["maskedEmail"] == "own*****@example.com"

    done = client.post(
        _COMPLETE,
        json={"linkToken": exchange["linkToken"], "action": "link", "password": "password123"},
    )
    assert done.status_code == 200
    assert done.json()["isNewUser"] is False

    account = db.scalar(
        select(UserSocialAccount).where(UserSocialAccount.provider_user_id == "link-1")
    )
    owner = db.scalar(select(User).where(User.email == "owner@example.com"))
    assert account.user_id == owner.id


def test_선점가입_공격_비번없이_연동불가_separate로_별도계정(
    client: TestClient, db: Session
) -> None:
    # 공격자가 피해자 이메일로 먼저 local 가입(비번은 공격자만 안다).
    _make_local(db, "victim@example.com", password="attacker-secret")
    exchange = client.post(
        _EXCHANGE,
        json={"code": _callback_to_code(client, _profile("victim-kakao", "victim@example.com"))},
    ).json()
    assert exchange["linkRequired"] is True
    link_token = exchange["linkToken"]

    # 피해자는 공격자 비번을 몰라 link 실패(그리고 링크 토큰은 소비되지 않는다).
    wrong = client.post(
        _COMPLETE,
        json={"linkToken": link_token, "action": "link", "password": "victim-guess"},
    )
    assert wrong.status_code == 401

    # 같은 링크 토큰으로 별도 계정 확보 가능(공격자 계정에 붙지 않는다).
    separate = client.post(_COMPLETE, json={"linkToken": link_token, "action": "separate"})
    assert separate.status_code == 200
    assert separate.json()["isNewUser"] is True
    assert separate.json()["user"]["email"] is None
    # 공격자 계정에는 소셜이 연결되지 않았다.
    victim_local = db.scalar(select(User).where(User.email == "victim@example.com"))
    assert (
        db.scalar(
            select(UserSocialAccount).where(UserSocialAccount.user_id == victim_local.id)
        )
        is None
    )


def test_link_토큰_재사용은_401(client: TestClient, db: Session) -> None:
    _make_local(db, "reuse@example.com", password="password123")
    code = _callback_to_code(client, _profile("reuse-1", "reuse@example.com"))
    exchange = client.post(_EXCHANGE, json={"code": code}).json()
    token = exchange["linkToken"]
    first = client.post(
        _COMPLETE, json={"linkToken": token, "action": "link", "password": "password123"}
    )
    assert first.status_code == 200
    second = client.post(
        _COMPLETE, json={"linkToken": token, "action": "link", "password": "password123"}
    )
    assert second.status_code == 401


# ---------------------------------------------------------------------------
# returnUrl 검증 — 호스트 정확 매칭 (서브도메인·서픽스·userinfo 우회 차단)
# ---------------------------------------------------------------------------


def test_returnurl_우회는_422_정상값은_통과(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        settings,
        "oauth_return_url_prefixes",
        "http://localhost,https://app.omeong.example,omeonggameong://",
    )
    _use_fake()

    def authorize(return_url: str) -> int:
        response = client.get(_AUTHORIZE, params={"returnUrl": return_url}, follow_redirects=False)
        return response.status_code

    # startswith 로는 통과하던 우회들 — 전부 422.
    assert authorize("http://localhost.evil.com/cb") == 422  # 서브도메인
    assert authorize("https://app.omeong.example.attacker.com/cb") == 422  # 서픽스
    assert authorize("http://localhost@evil.com/cb") == 422  # userinfo
    assert authorize("https://evil.com/cb") == 422  # 무관 호스트

    # 정상 값 — 통과(302).
    assert authorize("http://localhost:8081/auth/callback") == 302  # 포트 무관
    assert authorize("https://app.omeong.example/auth/callback") == 302
    assert authorize("omeonggameong://auth/callback") == 302  # 커스텀 스킴


def test_returnurl_비local_미설정이면_전부_422(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "oauth_return_url_prefixes", "")
    _use_fake()
    response = client.get(
        _AUTHORIZE, params={"returnUrl": "https://app.omeong.example/cb"}, follow_redirects=False
    )
    assert response.status_code == 422
