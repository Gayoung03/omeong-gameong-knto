"""인증 API 스키마 (docs/api/auth.md 확정 명세).

## 이메일 정규화를 한 곳에서

signup·login·check-email 이 같은 이메일을 서로 다르게 다루면(대소문자·공백)
"가입은 됐는데 로그인이 안 되는" 사고가 난다. 그래서 정규화(소문자+trim)를
`NormalizedEmail` 한 타입에 모아 세 곳이 공유한다. 형식 검증은 `EmailStr` 가 맡아
형식 오류는 422 로 나간다.

## 비밀번호는 SecretStr

평문이 로그·반복(repr)·검증 에러 에코에 새지 않도록 요청 스키마에서 `SecretStr`
로 받는다(Phase 1 의 422 input 제거와 함께 이중 방어). 규칙은 최소 8자·최대 128자.
"""

import uuid
from typing import Annotated, Literal

from pydantic import BeforeValidator, EmailStr, Field, SecretStr

from app.db.models.enums import AuthProvider
from app.schemas.base import APISchema
from app.schemas.pet import PetCreate
from app.schemas.travel_preference import TravelPreferenceUpsert
from app.schemas.user import Nickname

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128


def _normalize_email(value: object) -> object:
    return value.strip().lower() if isinstance(value, str) else value


#: 소문자+trim 정규화 후 형식 검증. signup·login·check-email 공용.
NormalizedEmail = Annotated[EmailStr, BeforeValidator(_normalize_email)]

#: 회원가입·회원탈퇴에서 쓰는 비밀번호. 규칙은 여기 한 곳.
Password = Annotated[
    SecretStr, Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)
]


class AuthUser(APISchema):
    """토큰 응답에 딸려 나가는 사용자 요약(auth.md 예시와 필드 일치)."""

    id: uuid.UUID
    email: str | None
    nickname: str
    profile_image_url: str | None
    auth_provider: AuthProvider
    status: Literal["active", "deleted"]


class TokenResponse(APISchema):
    """signup·login 공통 토큰 응답."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: AuthUser


class RefreshTokenResponse(APISchema):
    """`POST /auth/refresh` 응답 — user 객체는 포함하지 않는다(auth.md)."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class SignupRequest(APISchema):
    """계정+반려동물+여행취향을 한 요청으로 받는다(3단계 화면이 마지막에 일괄 제출).

    `pet` 은 기존 `PetCreate` 를 임베드해 speciesDetail 조건부 규칙을 그대로 상속한다.
    `authProvider` 는 클라이언트가 보내지 않는다 — 서버가 `local` 로 설정한다.
    """

    email: NormalizedEmail
    password: Password
    nickname: Nickname
    pet: PetCreate | None = None
    travel_preference: TravelPreferenceUpsert | None = None


class LoginRequest(APISchema):
    email: NormalizedEmail
    #: 로그인은 비밀번호 규칙(길이)을 노출하지 않는다 — 값만 받고 맞는지만 본다.
    password: SecretStr


class RefreshRequest(APISchema):
    refresh_token: str


class CheckEmailResponse(APISchema):
    available: bool
