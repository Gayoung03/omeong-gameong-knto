"""인증 전환(get_current_user JWT 검증) 통합 테스트.

`anon_client` 를 써서 인증 의존성의 **실제 구현**을 태운다. 환경은 autouse
`_neutralize_image_origin` 픽스처가 local 로 고정하므로, 비-local 케이스는 테스트에서
명시적으로 override 한다.
"""

import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.dependencies import DEV_USER_ID
from app.core.config import settings
from app.core.security import (
    ALGORITHM,
    create_access_token,
    create_refresh_token,
)
from app.db.models import User
from app.db.models.enums import AuthProvider

_ME = "/api/v1/users/me"


def _make_user(db: Session, *, user_id: uuid.UUID | None = None, deleted: bool = False) -> User:
    user = User(
        id=user_id or uuid.uuid4(),
        nickname="가드",
        email=f"{uuid.uuid4().hex}@guard.local",
        auth_provider=AuthProvider.LOCAL,
    )
    if deleted:
        user.deleted_at = datetime.now(UTC)
    db.add(user)
    db.flush()
    return user


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _expired_access(user_id: uuid.UUID) -> str:
    now = datetime.now(UTC)
    claims = {
        "sub": str(user_id),
        "typ": "access",
        "jti": uuid.uuid4().hex,
        "iat": int((now - timedelta(hours=1)).timestamp()),
        "exp": int((now - timedelta(minutes=1)).timestamp()),
    }
    return jwt.encode(claims, settings.secret_key, algorithm=ALGORITHM)


# ---------------------------------------------------------------------------
# 유효 토큰
# ---------------------------------------------------------------------------


def test_유효한_access_토큰은_200_이고_그_사용자다(
    anon_client: TestClient, db: Session
) -> None:
    user = _make_user(db)
    response = anon_client.get(_ME, headers=_bearer(create_access_token(user.id)))

    assert response.status_code == 200
    assert response.json()["id"] == str(user.id)


# ---------------------------------------------------------------------------
# 헤더 없음 — 환경에 따라 갈린다
# ---------------------------------------------------------------------------


def test_헤더_없음_비local은_401(
    anon_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # autouse 픽스처가 local 로 고정하므로 여기서 명시적으로 뒤집는다.
    monkeypatch.setattr(settings, "environment", "production")
    response = anon_client.get(_ME)
    assert response.status_code == 401


def test_헤더_없음_local은_DEV_사용자로_폴백_200(
    anon_client: TestClient, db: Session
) -> None:
    # 폴백 대상인 고정 사용자를 심어둔다(환경은 이미 local).
    _make_user(db, user_id=DEV_USER_ID)
    response = anon_client.get(_ME)

    assert response.status_code == 200
    assert response.json()["id"] == str(DEV_USER_ID)


# ---------------------------------------------------------------------------
# 헤더 있음 — 실패 경로는 전부 401
# ---------------------------------------------------------------------------


def test_만료된_토큰은_401(anon_client: TestClient, db: Session) -> None:
    user = _make_user(db)
    response = anon_client.get(_ME, headers=_bearer(_expired_access(user.id)))
    assert response.status_code == 401


def test_위조된_토큰은_401(anon_client: TestClient, db: Session) -> None:
    user = _make_user(db)
    forged = jwt.encode(
        {
            "sub": str(user.id),
            "typ": "access",
            "jti": uuid.uuid4().hex,
            "iat": int(datetime.now(UTC).timestamp()),
            "exp": int((datetime.now(UTC) + timedelta(minutes=5)).timestamp()),
        },
        "wrong-secret-key",
        algorithm=ALGORITHM,
    )
    response = anon_client.get(_ME, headers=_bearer(forged))
    assert response.status_code == 401


def test_refresh_토큰으로_인증하면_401(anon_client: TestClient, db: Session) -> None:
    user = _make_user(db)
    # typ=refresh 를 access 자리에 쓰면 거부된다.
    response = anon_client.get(_ME, headers=_bearer(create_refresh_token(user.id)))
    assert response.status_code == 401


def test_탈퇴_사용자의_유효_토큰도_401(anon_client: TestClient, db: Session) -> None:
    user = _make_user(db, deleted=True)
    # 토큰 자체는 유효하지만 deleted_at 이 있어 401.
    response = anon_client.get(_ME, headers=_bearer(create_access_token(user.id)))
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# optional 경로
# ---------------------------------------------------------------------------


def test_optional_경로는_헤더_없이도_200(anon_client: TestClient) -> None:
    # 장소 목록은 비로그인 조회 허용(get_optional_user). local 에서 헤더 없이 200.
    response = anon_client.get("/api/v1/places")
    assert response.status_code == 200


def test_optional_경로도_잘못된_토큰은_401(anon_client: TestClient) -> None:
    # 헤더가 "있는데 틀린" 것은 optional 이라도 조용히 넘기지 않는다.
    response = anon_client.get("/api/v1/places", headers=_bearer("not.a.jwt"))
    assert response.status_code == 401
