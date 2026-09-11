"""점수화된 장소를 일자별 일정으로 조립하는 패키지.

기존 단일 모듈(app.recommend.itinerary)의 공개 이름(build·BuildRequest·RouteAnchor·
Scheduled*/Itinerary*·UnfilledSlot·시간 상수·MAX_*)을 그대로 노출해 서비스·테스트의
import 경로를 유지하고, Phase 5 에서 추가한 SlotSearchContext·top_alternatives 도 함께
노출한다. plan_day·DaySlot 등 내부 구성 요소는 하위 모듈에서 직접 import 한다.
"""

from .build import build
from .select import SlotSearchContext, top_alternatives
from .types import (
    DINNER_START,
    DINNER_START_BY,
    KST,
    LUNCH_START,
    LUNCH_START_BY,
    MAX_ALTERNATIVES,
    MAX_TMAP_CALLS_PER_DAY,
    BuildRequest,
    Itinerary,
    ItineraryDay,
    RouteAnchor,
    ScheduledItem,
    ScheduledMove,
    UnfilledSlot,
)

__all__ = [
    "DINNER_START",
    "DINNER_START_BY",
    "KST",
    "LUNCH_START",
    "LUNCH_START_BY",
    "MAX_ALTERNATIVES",
    "MAX_TMAP_CALLS_PER_DAY",
    "BuildRequest",
    "Itinerary",
    "ItineraryDay",
    "RouteAnchor",
    "ScheduledItem",
    "ScheduledMove",
    "SlotSearchContext",
    "UnfilledSlot",
    "build",
    "top_alternatives",
]
