"""이메일 인증 엔드포인트 통합 테스트 (signup·login·refresh)."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Pet, User, UserTravelPreference


def _signup_body(email: str = "traveler@example.com", **overrides) -> dict:
    body = {
        "email": email,
        "password": "password123",
        "nickname": "여행자",
        "pet": {"name": "몽이", "species": "dog", "size": "small"},
        "travelPreference": {
            "preferredDurationDays": 2,
            "defaultTransport": "rental_car",
            "departureLocation": "제주시",
            "preferredTags": ["바다", "카페"],
            "companionCount": 1,
        },
    }
    body.update(overrides)
    return body


# ---------------------------------------------------------------------------
# signup
# ---------------------------------------------------------------------------


def test_회원가입은_토큰과_사용자를_돌려주고_세_테이블을_채운다(
    client: TestClient, db: Session
) -> None:
    response = client.post("/api/v1/auth/signup", json=_signup_body())

    assert response.status_code == 201
    body = response.json()
    assert body["accessToken"]
    assert body["refreshToken"]
    assert body["tokenType"] == "bearer"
    assert body["expiresIn"] == 1800
    assert body["user"]["email"] == "traveler@example.com"
    assert body["user"]["nickname"] == "여행자"
    assert body["user"]["authProvider"] == "local"
    assert body["user"]["status"] == "active"
    assert body["user"]["profileImageUrl"] is None

    user = db.scalar(select(User).where(User.email == "traveler@example.com"))
    assert user is not None
    assert user.password_hash and user.password_hash != "password123"  # 평문 저장 아님
    pet = db.scalar(select(Pet).where(Pet.user_id == user.id))
    assert pet is not None and pet.is_primary is True  # 첫 펫 자동 대표
    pref = db.get(UserTravelPreference, user.id)
    assert pref is not None and pref.companion_count == 1


def test_펫_취향_없이도_가입되고_기본_취향_행이_생긴다(
    client: TestClient, db: Session
) -> None:
    response = client.post(
        "/api/v1/auth/signup",
        json={"email": "solo@example.com", "password": "password123", "nickname": "혼자"},
    )

    assert response.status_code == 201
    user = db.scalar(select(User).where(User.email == "solo@example.com"))
    assert db.scalar(select(Pet).where(Pet.user_id == user.id)) is None
    pref = db.get(UserTravelPreference, user.id)
    assert pref is not None and pref.companion_count == 1


def test_이메일은_소문자_trim_정규화된다(client: TestClient, db: Session) -> None:
    response = client.post(
        "/api/v1/auth/signup", json=_signup_body(email="  Traveler@Example.COM  ")
    )
    assert response.status_code == 201
    assert response.json()["user"]["email"] == "traveler@example.com"
    assert db.scalar(select(User.id).where(User.email == "traveler@example.com")) is not None


def test_잘못된_펫이면_유저도_만들어지지_않는다(client: TestClient, db: Session) -> None:
    # species=other 인데 speciesDetail 이 없다 → PetCreate 검증 실패(422).
    response = client.post(
        "/api/v1/auth/signup",
        json=_signup_body(
            email="atomic@example.com", pet={"name": "몽이", "species": "other"}
        ),
    )

    assert response.status_code == 422
    # 트랜잭션이 통째로 무산돼 유저가 남지 않는다.
    assert db.scalar(select(User.id).where(User.email == "atomic@example.com")) is None


def test_중복_이메일은_409(client: TestClient) -> None:
    client.post("/api/v1/auth/signup", json=_signup_body(email="dup@example.com"))
    again = client.post("/api/v1/auth/signup", json=_signup_body(email="dup@example.com"))
    assert again.status_code == 409


def test_탈퇴한_이메일_재가입도_409(client: TestClient, db: Session) -> None:
    client.post("/api/v1/auth/signup", json=_signup_body(email="gone@example.com"))
    user = db.scalar(select(User).where(User.email == "gone@example.com"))
    user.deleted_at = datetime.now(UTC)
    db.flush()

    again = client.post("/api/v1/auth/signup", json=_signup_body(email="gone@example.com"))
    assert again.status_code == 409


def test_비밀번호_규칙_미달은_422(client: TestClient) -> None:
    short = client.post("/api/v1/auth/signup", json=_signup_body(password="short"))
    assert short.status_code == 422


# ---------------------------------------------------------------------------
# login
# ---------------------------------------------------------------------------


def test_로그인_성공은_토큰을_준다(client: TestClient) -> None:
    client.post("/api/v1/auth/signup", json=_signup_body(email="login@example.com"))

    response = client.post(
        "/api/v1/auth/login", json={"email": "login@example.com", "password": "password123"}
    )
    assert response.status_code == 200
    assert response.json()["accessToken"]
    assert response.json()["user"]["email"] == "login@example.com"


def test_비번_불일치와_없는_이메일은_같은_401(client: TestClient) -> None:
    client.post("/api/v1/auth/signup", json=_signup_body(email="real@example.com"))

    wrong_password = client.post(
        "/api/v1/auth/login", json={"email": "real@example.com", "password": "wrongpassword"}
    )
    missing_email = client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "password123"}
    )

    assert wrong_password.status_code == 401
    assert missing_email.status_code == 401
    assert wrong_password.json() == missing_email.json()  # 사유 미구분


def test_탈퇴_계정_로그인은_401(client: TestClient, db: Session) -> None:
    client.post("/api/v1/auth/signup", json=_signup_body(email="left@example.com"))
    user = db.scalar(select(User).where(User.email == "left@example.com"))
    user.deleted_at = datetime.now(UTC)
    db.flush()

    response = client.post(
        "/api/v1/auth/login", json={"email": "left@example.com", "password": "password123"}
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# refresh
# ---------------------------------------------------------------------------


def test_재발급은_새_access와_같은_refresh를_준다(client: TestClient) -> None:
    signed = client.post(
        "/api/v1/auth/signup", json=_signup_body(email="refresh@example.com")
    ).json()

    response = client.post(
        "/api/v1/auth/refresh", json={"refreshToken": signed["refreshToken"]}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["accessToken"]
    # 회전 없음: 응답 refreshToken == 요청 refreshToken.
    assert body["refreshToken"] == signed["refreshToken"]
    assert "user" not in body


def test_access_토큰으로_재발급하면_401(client: TestClient) -> None:
    signed = client.post(
        "/api/v1/auth/signup", json=_signup_body(email="cross@example.com")
    ).json()

    # access token 을 refresh 로 쓰면 typ 불일치 → 401.
    response = client.post(
        "/api/v1/auth/refresh", json={"refreshToken": signed["accessToken"]}
    )
    assert response.status_code == 401


def test_위조_토큰_재발급은_401(client: TestClient) -> None:
    response = client.post("/api/v1/auth/refresh", json={"refreshToken": "not.a.jwt"})
    assert response.status_code == 401


def test_탈퇴_사용자_재발급은_401(client: TestClient, db: Session) -> None:
    signed = client.post(
        "/api/v1/auth/signup", json=_signup_body(email="refleft@example.com")
    ).json()
    user = db.scalar(select(User).where(User.email == "refleft@example.com"))
    user.deleted_at = datetime.now(UTC)
    db.flush()

    response = client.post(
        "/api/v1/auth/refresh", json={"refreshToken": signed["refreshToken"]}
    )
    assert response.status_code == 401
