"""여행(route) API 스키마."""

import uuid
from datetime import date, datetime

from pydantic import Field, computed_field, model_validator

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


# ---------------------------------------------------------------------------
# 일정 편집 (docs/api/routes.md "일정 편집")
# ---------------------------------------------------------------------------
# 조회용 스키마와 달리 이쪽은 **앱이 보내는 것**을 받는다. 그래서 검증이 붙는다.
# 여기서 막지 않으면 DB CheckConstraint 가 막고, 그건 500 으로 나가서
# 앱이 "무엇이 잘못됐는지" 알 수 없다. 422 로 돌려주려면 여기서 걸러야 한다.


class RouteItemCreate(APISchema):
    """하루에 방문 한 건을 추가할 때 앱이 보내는 것."""

    item_type: ScheduleItemType
    sort_order: int = Field(ge=0, description="0 이상. 이미 있는 값이면 뒤 항목을 밀어낸다")
    place_id: uuid.UUID | None = None
    custom_place_name: str | None = Field(default=None, max_length=200)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    stay_minutes: int | None = Field(default=None, ge=0)
    note: str | None = None

    @model_validator(mode="after")
    def _check_place_and_time(self) -> "RouteItemCreate":
        # DB 에는 이 조합 제약이 없다. 등록된 장소가 아닌 "직접 입력" 일정을
        # 허용하되, 이름조차 없는 빈 일정은 화면에 그릴 수 없어서 막는다.
        if self.place_id is None and not self.custom_place_name:
            raise ValueError("placeId 또는 customPlaceName 중 하나는 있어야 합니다")
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValueError("endsAt 은 startsAt 보다 뒤여야 합니다")
        return self


class RouteItemUpdate(APISchema):
    """일정 항목 수정. **보낸 필드만** 바꾼다.

    전부 기본값이 None 이라 "안 보냈다"와 "null 로 비워달라"가 값만으로는
    구분되지 않는다. 그래서 엔드포인트에서 model_dump(exclude_unset=True) 로
    실제로 보낸 필드만 꺼내 쓴다. 순서(sortOrder)는 여기서 못 바꾼다 —
    UNIQUE 제약 때문에 순서 API 로 한 번에 보내야 한다.
    """

    starts_at: datetime | None = None
    ends_at: datetime | None = None
    stay_minutes: int | None = Field(default=None, ge=0)
    note: str | None = None
    is_selected: bool | None = None


class RouteItemOrderUpdate(APISchema):
    """드래그로 순서를 바꿨을 때. 그 날짜의 항목 전체를 순서대로 보낸다."""

    item_ids: list[uuid.UUID] = Field(min_length=1)


# ---------------------------------------------------------------------------
# 여행 관리 (PATCH · 공유)
# ---------------------------------------------------------------------------


class RouteUpdate(APISchema):
    """여행 수정. 보낸 필드만 바꾼다.

    `status` 는 아무 값이나 받지 않는다. 허용 전이는 엔드포인트에 표로 두었다.
    `isPublic` 을 false 로 보내는 것이 곧 **공유 해제**다(별도 엔드포인트가 없다).
    """

    title: str | None = Field(default=None, min_length=1, max_length=150)
    status: RouteStatus | None = None
    style_keywords: list[str] | None = None
    memo: str | None = None
    cover_image_url: str | None = None
    is_public: bool | None = None


class RouteShareResponse(APISchema):
    """공유 링크 발급 결과."""

    share_token: str
    is_public: bool


class SharedRouteDetail(RouteListItem):
    """공유 링크로 보는 여행.

    RouteDetail 에서 **memo 와 shareToken 을 뺐다.** 개인 메모는 남에게 보일
    것이 아니고, 토큰은 그것을 본 사람이 다시 퍼뜨릴 수 있는 값이다.
    체크리스트·메모는 애초에 별도 엔드포인트라 여기 담기지 않는다.
    """

    explanation: str | None
    total_score: float | None
    pets: list[RoutePetResponse]
    route_days: list[RouteDayResponse]


# ---------------------------------------------------------------------------
# 체크리스트
# ---------------------------------------------------------------------------


class ChecklistItemResponse(APISchema):
    id: uuid.UUID
    category: str
    label: str
    is_checked: bool
    is_recommended: bool
    sort_order: int


class ChecklistItemListResponse(APISchema):
    items: list[ChecklistItemResponse]
    total: int
    limit: int
    offset: int


class ChecklistItemCreate(APISchema):
    """사용자가 직접 추가하는 항목.

    `isRecommended` 를 받지 않는다. 서버가 false 로 고정한다 — 앱이 보낸 값을
    믿으면 사용자가 만든 항목이 '기본 제공'으로 둔갑할 수 있다.
    """

    category: str = Field(max_length=30)
    label: str = Field(min_length=1, max_length=200)
    sort_order: int = Field(default=0, ge=0)


class ChecklistItemUpdate(APISchema):
    label: str | None = Field(default=None, min_length=1, max_length=200)
    is_checked: bool | None = None
    sort_order: int | None = Field(default=None, ge=0)


# ---------------------------------------------------------------------------
# 메모
# ---------------------------------------------------------------------------


class MemoResponse(APISchema):
    id: uuid.UUID
    route_day_id: uuid.UUID | None
    title: str | None
    content: str
    created_at: datetime
    updated_at: datetime


class MemoListResponse(APISchema):
    items: list[MemoResponse]
    total: int
    limit: int
    offset: int


class MemoCreate(APISchema):
    """`routeDayId` 가 null 이면 여행 전체 메모, 값이 있으면 그 일차 메모다."""

    route_day_id: uuid.UUID | None = None
    title: str | None = Field(default=None, max_length=150)
    content: str = Field(min_length=1)


class MemoUpdate(APISchema):
    """`routeDayId` 는 없다. 명세상 다른 일차로 옮기려면 지우고 다시 쓴다."""

    title: str | None = Field(default=None, max_length=150)
    content: str | None = Field(default=None, min_length=1)
