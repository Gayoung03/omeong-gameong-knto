"""여행(route) API 스키마."""

import uuid
from datetime import date, datetime

from pydantic import computed_field

from app.db.models.enums import (
    PetSize,
    PetSpecies,
    RouteCreationType,
    RouteStatus,
    ScheduleItemType,
    TransportType,
    TripPace,
)
from app.schemas.base import APISchema


class RouteListItem(APISchema):
    """내 여행 목록의 한 줄. docs/api/routes.md 의 GET /routes 응답."""

    id: uuid.UUID
    title: str
    status: RouteStatus
    creation_type: RouteCreationType
    version: int
    start_at: datetime
    end_at: datetime
    pace: TripPace
    transport: TransportType
    cover_image_url: str | None
    style_keywords: list[str] | None
    # Numeric 은 그대로 두면 문자열로 나간다. 명세가 숫자(92.5)라 float 로 받는다.
    pet_safety_score: float | None
    is_public: bool

    # --- 계산값 (docs/api/README.md 6장) ---------------------------------
    # DB 에 저장하지 않고 조회할 때 만든다. start_at/end_at 은 KST(+09:00) 로
    # 돌아오므로 .date() 가 한국 날짜다.

    @computed_field
    @property
    def days(self) -> int:
        return (self.end_at.date() - self.start_at.date()).days + 1

    @computed_field
    @property
    def nights(self) -> int:
        return max(self.days - 1, 0)


class RouteListResponse(APISchema):
    """목록 응답은 배열을 그대로 내리지 않고 감싼다 (docs/api/README.md 5장)."""

    items: list[RouteListItem]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# 상세 (GET /routes/{routeId})
# ---------------------------------------------------------------------------
# 오늘 넣지 않은 명세 필드: weather · moveToNext · distanceSummary · stays ·
# logCount · place 의 rating/reviewCount/petPolicyType.
# 전부 아직 데이터 소스가 없다(기상청·TMAP·리뷰 집계·place_pet_policies).


class PlaceSummary(APISchema):
    """일정에 담긴 장소 요약."""

    id: uuid.UUID
    name: str
    category: str
    address: str | None
    description: str | None
    primary_image_url: str | None
    latitude: float
    longitude: float
    reservation_required: bool


class RouteItemResponse(APISchema):
    """하루 안의 방문 한 건. DB 의 route_items 한 줄이다."""

    id: uuid.UUID
    sort_order: int
    item_type: ScheduleItemType
    starts_at: datetime | None
    ends_at: datetime | None
    stay_minutes: int | None
    note: str | None
    is_selected: bool
    recommendation_score: float | None
    recommendation_reason: str | None
    custom_place_name: str | None
    place: PlaceSummary | None


class RouteDayResponse(APISchema):
    """여행의 하루."""

    id: uuid.UUID
    day_number: int
    route_date: date
    title: str | None
    items: list[RouteItemResponse]


class RoutePetResponse(APISchema):
    """이 여행에 함께 가는 반려동물."""

    id: uuid.UUID
    name: str
    species: PetSpecies
    species_detail: str | None
    size: PetSize | None


class RouteDetail(RouteListItem):
    """목록 필드 + 상세 전용 필드."""

    explanation: str | None
    total_score: float | None
    memo: str | None
    share_token: str | None
    pets: list[RoutePetResponse]
    route_days: list[RouteDayResponse]
