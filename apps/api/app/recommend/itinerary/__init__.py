"""점수화된 장소를 일자별 일정으로 조립하는 패키지.

기존 단일 모듈(app.recommend.itinerary)과 같은 공개 이름을 그대로 노출한다.
서비스·테스트의 import 경로는 바뀌지 않는다.
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
