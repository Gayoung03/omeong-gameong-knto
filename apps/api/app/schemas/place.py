"""장소 API 스키마.

목록·상세의 상당수가 **계산값**이다(거리·리뷰수·저장수·평점·즐겨찾기 여부).
DB 컬럼이 아니라서 `model_validate(place)` 로 한 번에 만들 수 없고,
엔드포인트가 값을 채워 넣는다. 그래서 이 파일의 스키마는 "응답의 모양"만 정한다.
"""

import uuid
from datetime import datetime, time

from pydantic import Field

from app.db.models.enums import DataProvider, PetPolicyType, PlaceEnvironment
from app.schemas.base import APISchema


class PlaceTagResponse(APISchema):
    code: str
    name: str


class PlaceTagListResponse(APISchema):
    items: list[PlaceTagResponse]
    total: int
    limit: int
    offset: int


class PlaceListItem(APISchema):
    """목록 한 줄. 영업시간·상세 정책은 상세 조회에만 있다."""

    id: uuid.UUID
    name: str
    category: str
    region: str | None
    address: str | None
    road_address: str | None
    latitude: float
    longitude: float
    primary_image_url: str | None
    environment: PlaceEnvironment | None
    # 정책 행이 아예 없는 장소도 unknown 으로 내린다. 앱은 회색 "정보 없음"
    # 배지를 그린다 — 배지를 안 그리면 카드 높이가 들쭉날쭉해진다.
    pet_policy_type: PetPolicyType
    tags: list[str]
    reservation_required: bool
    distance_meters: int | None
    review_count: int
    saved_count: int
    rating: float | None
    is_favorite: bool


class PlaceListResponse(APISchema):
    items: list[PlaceListItem]
    total: int
    limit: int
    offset: int


class FavoritePlaceItem(PlaceListItem):
    favorited_at: datetime


class FavoritePlaceListResponse(APISchema):
    items: list[FavoritePlaceItem]
    total: int
    limit: int
    offset: int


class PetPolicyResponse(APISchema):
    policy_type: PetPolicyType
    allowed_species: list[str] | None
    allowed_sizes: list[str] | None
    max_weight_kg: float | None
    carrier_required: bool | None
    leash_required: bool | None
    vaccination_required: bool | None
    extra_fee_amount: int | None
    notes: str | None
    source: DataProvider | None
    source_url: str | None
    verified_at: datetime | None
    reliability_score: float | None
    # AI 입출력 컬럼(ai-io-column-design 7.1). nullable — 3값 의미 유지.
    muzzle_required: bool | None
    food_area_allowed: bool | None
    max_pets_per_person: int | None
    caution_note: str | None


class BusinessHourResponse(APISchema):
    """`dayOfWeek` 는 0(일요일) ~ 6(토요일). DB CHECK 제약과 같다."""

    day_of_week: int
    opens_at: time | None
    closes_at: time | None
    break_start_at: time | None
    break_end_at: time | None
    is_closed: bool
    raw_text: str | None


class PlaceDetail(APISchema):
    id: uuid.UUID
    name: str
    category: str
    # etc 세부 분류(예: 동물약국). category 는 불변 enum, 이 필드가 세분화를 담는다. null 가능.
    category_detail: str | None
    region: str | None
    address: str | None
    road_address: str | None
    latitude: float
    longitude: float
    phone: str | None
    homepage_url: str | None
    primary_image_url: str | None
    description: str | None
    description_source: DataProvider | None
    environment: PlaceEnvironment | None
    amenities: list[str] | None
    average_stay_minutes: int | None
    # 숙박 체크인/아웃(신규 가산 필드). 한쪽만 알 수 있어 짝을 강제하지 않는다. null 가능.
    check_in_time: time | None
    check_out_time: time | None
    reservation_required: bool
    # created_by_user_id 가 있으면 true. **사용자 id 자체는 내리지 않는다.**
    is_user_created: bool
    tags: list[PlaceTagResponse]
    pet_policy: PetPolicyResponse
    business_hours: list[BusinessHourResponse]
    review_count: int
    saved_count: int
    rating: float | None
    is_favorite: bool


class PlaceCreate(APISchema):
    """나만의 장소 등록.

    `descriptionSource` 를 받지 않는다 — 서버가 `internal` 로 고정한다.
    출처를 앱이 정하게 두면 사용자가 등록한 장소가 관광공사 데이터인 척할 수 있다.
    """

    name: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=50)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    address: str | None = None
    road_address: str | None = None
    phone: str | None = Field(default=None, max_length=50)
    primary_image_url: str | None = None
    description: str | None = None
