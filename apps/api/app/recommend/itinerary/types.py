"""일정 조립 패키지의 공용 타입·상수.

조립기가 만드는 결과 구조(하루·항목·이동·빈 슬롯)와 여러 모듈이 공유하는
시간 상수를 모은다. select·fit·build 가 이 모듈을 import 하고, 순환을 피하려
이 모듈은 같은 패키지의 다른 모듈을 import 하지 않는다.
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from app.db.models.enums import ScheduleItemType, TransportType, TripPace
from app.recommend.config.pace import PaceRule
from app.recommend.schemas import ScoredCandidate
from app.recommend.tmap import RouteLeg

KST = ZoneInfo("Asia/Seoul")
DINNER_START = time(17)
DINNER_START_BY = time(19, 30)
LUNCH_START = time(11, 30)
LUNCH_START_BY = time(14)

Coordinate = tuple[float, float]
RouteProvider = Callable[[Coordinate, Coordinate, TransportType, datetime | None], RouteLeg]

# 못 채운 식사 슬롯의 안내 문구(응답 recommendation_reason).
UNFILLED_MEAL_REASON = (
    "확실히 동반 가능한 식당을 찾지 못했어요. 아래 후보는 동반 여부 확인이 필요해요."
)
MAX_ALTERNATIVES = 3

# 후보가 계속 시간 제약에 안 맞으면 후보 수만큼 TMAP(타임아웃 10초)을 부를 수 있어
# 폴링 한도(3분)를 넘긴다. 하루당 호출을 이 상한으로 묶고, 초과분은 직선거리 추정으로
# 대체해 일정 조립을 계속 진행한다.
MAX_TMAP_CALLS_PER_DAY = 12


@dataclass(frozen=True)
class BuildRequest:
    start_at: datetime
    end_at: datetime
    pace: TripPace
    transport: TransportType
    start_coord: Coordinate
    restaurant_preferred: bool = False
    day_start_anchors: dict[date, "RouteAnchor"] = field(default_factory=dict)
    day_end_anchors: dict[date, "RouteAnchor"] = field(default_factory=dict)
    # 반려동물 특성 반영 하루 구성 규칙. None 이면 PACE 표를 쓴다.
    pace_rule: PaceRule | None = None


@dataclass(frozen=True)
class RouteAnchor:
    """사용자가 지정한 출발지 또는 숙소."""

    name: str
    coord: Coordinate
    item_type: ScheduleItemType
    place_id: uuid.UUID | None = None
    address: str | None = None


@dataclass(frozen=True)
class ScheduledItem:
    candidate: ScoredCandidate
    starts_at: datetime
    ends_at: datetime


@dataclass(frozen=True)
class ScheduledMove:
    transport: TransportType
    route: RouteLeg


@dataclass(frozen=True)
class UnfilledSlot:
    """못 채운 슬롯. item_type 은 의도한 유형(예: restaurant), candidates 는 확인 필요 후보."""

    item_type: ScheduleItemType
    position: int
    reason: str
    candidates: tuple[ScoredCandidate, ...] = ()


@dataclass(frozen=True)
class ItineraryDay:
    route_date: date
    items: tuple[ScheduledItem, ...]
    moves: tuple[ScheduledMove, ...]
    dinner_required: bool
    restaurant_required: bool
    start_anchor: RouteAnchor | None = None
    end_anchor: RouteAnchor | None = None
    day_start: datetime | None = None
    end_arrival: datetime | None = None
    unfilled: tuple[UnfilledSlot, ...] = ()
    # 채워진 항목별 대안 후보(최대 3). key 는 chosen place_id.
    alternatives: dict[uuid.UUID, tuple[ScoredCandidate, ...]] = field(default_factory=dict)


@dataclass(frozen=True)
class Itinerary:
    days: tuple[ItineraryDay, ...]
