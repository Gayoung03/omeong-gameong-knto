"""여행 취향(user_travel_preferences) API 스키마.

가입(`POST /auth/signup`)의 임베드와 `PUT /users/me/travel-preference` 가 같은
요청 스키마를 공유한다. PUT 은 "전체 덮어쓰기"(docs/api/users.md)라, 보내지 않은
필드는 기본값(대개 null, `companionCount` 는 1)으로 채워 upsert 에 넘긴다.

enum·태그 값은 영문 코드 그대로다 — `rental_car` 의 밑줄은 표기법이 아니라 값의
일부라 camelCase 로 바꾸지 않는다(필드명만 camelCase).
"""

from datetime import datetime

from pydantic import Field

from app.db.models.enums import TransportType, TripPace
from app.schemas.base import APISchema


class TravelPreferenceUpsert(APISchema):
    """취향 생성/수정 요청. 값 제약은 DB CheckConstraint 와 일치시킨다.

    `companionCount` 는 기본 1(모델 server_default 와 같음)이라 안 보내면 1 이 된다.
    `>=1` 은 여기서 막아 422 로 돌려준다 — DB CHECK 로만 두면 500 이 나간다.
    """

    default_pace: TripPace | None = None
    default_transport: TransportType | None = None
    departure_location: str | None = Field(default=None, max_length=100)
    preferred_duration_days: int | None = Field(default=None, ge=1)
    companion_count: int = Field(default=1, ge=1)
    preferred_tags: list[str] | None = None


class TravelPreferenceResponse(APISchema):
    """`GET /users/me/travel-preference` 응답.

    취향을 한 번도 저장하지 않은 사용자는 행이 없을 수 있어 `updatedAt` 이 null 일
    수 있다(엔드포인트가 기본값 모양으로 합성).
    """

    default_pace: TripPace | None
    default_transport: TransportType | None
    departure_location: str | None
    preferred_duration_days: int | None
    companion_count: int
    preferred_tags: list[str] | None
    updated_at: datetime | None
