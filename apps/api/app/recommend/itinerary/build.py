"""점수화된 장소를 시간 제약이 있는 일자별 일정으로 조립한다.

build() 는 하루 단위로 plan_day 의 슬롯 구성을 그리디로 채운다. 하루의 고정 정보는
_DayContext, 채워 나가는 상태는 _DayBuildState, TMAP 호출 예산은 _TmapBudget 으로
분리해 루프 본문을 _meal_slot_for(식사 트리거)·_place_candidate(방문 배치)·
_finalize_day(안전망·앵커·복귀)로 나눈다.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from app.db.models.enums import PlaceEnvironment, ScheduleItemType, TransportType
from app.recommend.config.pace import PACE, PaceRule
from app.recommend.schemas import ScoredCandidate
from app.recommend.tmap import RouteLeg, TMapError
from app.recommend.travel_estimate import SUPPORTED_TRANSPORTS, estimate_leg

from .fit import fit_visit
from .plan import plan_day
from .select import (
    SlotSearchContext,
    best_candidate_with_diversity,
    meal_unfilled_slot,
    top_alternatives,
)
from .types import (
    DINNER_START,
    DINNER_START_BY,
    KST,
    LUNCH_START,
    LUNCH_START_BY,
    MAX_TMAP_CALLS_PER_DAY,
    BuildRequest,
    Coordinate,
    Itinerary,
    ItineraryDay,
    RouteAnchor,
    RouteProvider,
    ScheduledItem,
    ScheduledMove,
    UnfilledSlot,
)

logger = logging.getLogger(__name__)

EnvSpec = tuple[PlaceEnvironment | None, bool]


@dataclass
class _TmapBudget:
    """여행 전체의 TMAP 호출 예산. 하루 상한을 넘거나 오류가 나면 직선거리 추정으로 뗀다."""

    transport: TransportType
    get_route: RouteProvider
    available: bool = True
    _route_calls: int = 0
    _cap_logged: bool = False

    def start_day(self) -> None:
        self._route_calls = 0
        self._cap_logged = False

    def leg(
        self, origin: Coordinate, destination: Coordinate, depart_at: datetime, day: date
    ) -> RouteLeg:
        """상한 이내·TMAP 정상일 때는 실제 경로를, 그 외에는 직선거리 추정을 돌려준다."""
        if self.available and self._route_calls >= MAX_TMAP_CALLS_PER_DAY and not self._cap_logged:
            logger.warning(
                "TMAP 호출 상한(%d) 도달 — %s 이후 구간은 직선거리로 추정합니다",
                MAX_TMAP_CALLS_PER_DAY,
                day,
            )
            self._cap_logged = True
        if not self.available or self._route_calls >= MAX_TMAP_CALLS_PER_DAY:
            return estimate_leg(origin, destination, self.transport)
        try:
            leg = self.get_route(origin, destination, self.transport, depart_at)
        except TMapError:
            logger.warning(
                "TMAP 조회 실패 — 이번 여행의 이후 구간은 직선거리로 추정합니다",
                exc_info=True,
            )
            self.available = False
            return estimate_leg(origin, destination, self.transport)
        # 캐시 적중·추정은 상한에서 제외하고 실제 TMAP 호출만 센다.
        if leg.source == "tmap":
            self._route_calls += 1
        return leg


@dataclass(frozen=True)
class _DayContext:
    """하루를 채우는 동안 바뀌지 않는 정보(창·앵커·식사 필요·슬롯 환경)."""

    route_date: date
    day_start: datetime
    day_end: datetime
    dinner_start: datetime
    dinner_start_by: datetime
    lunch_start: datetime
    lunch_start_by: datetime
    places_per_day: int
    dinner_required: bool
    lunch_required: bool
    activity_envs: list[EnvSpec]
    end_coord: Coordinate | None
    start_anchor: RouteAnchor | None
    end_anchor: RouteAnchor | None
    rule: PaceRule
    transport: TransportType


@dataclass
class _DayBuildState:
    """하루를 채워 나가며 바뀌는 상태."""

    current_coord: Coordinate
    current_time: datetime
    items: list[ScheduledItem] = field(default_factory=list)
    moves: list[ScheduledMove] = field(default_factory=list)
    unfilled: list[UnfilledSlot] = field(default_factory=list)
    alternatives: dict[uuid.UUID, tuple[ScoredCandidate, ...]] = field(default_factory=dict)
    rejected_today: set[uuid.UUID] = field(default_factory=set)
    activities_placed: int = 0
    restaurant_scheduled: bool = False
    # 필요한 식사를 빈 슬롯으로 처리했으면 True. 이후엔 식사 슬롯을 다시 시도하지 않고
    # 남은 시간에 관광 후보를 계속 배치한다(빈 슬롯이 슬롯 개수를 하나 차지한다).
    meal_unfilled: bool = False

    @property
    def slot_count(self) -> int:
        return len(self.items) + len(self.unfilled)


@dataclass(frozen=True)
class _MealSlot:
    """이번 슬롯이 식사 슬롯인지와, 그에 따른 시각·유형 제약."""

    is_meal: bool
    is_dinner: bool
    not_before: datetime | None
    start_by: datetime | None
    visit_deadline: datetime
    blocked_types: frozenset[ScheduleItemType]
    required_type: ScheduleItemType | None


def build(
    scored: list[ScoredCandidate], request: BuildRequest, get_route: RouteProvider
) -> Itinerary:
    """직선거리로 후보를 좁히고 선택한 구간만 실제 경로를 조회한다."""

    start_at = _as_kst(request.start_at)
    end_at = _as_kst(request.end_at)
    if end_at <= start_at:
        raise ValueError("여행 종료 시각은 시작 시각보다 늦어야 합니다")
    if request.transport not in SUPPORTED_TRANSPORTS:
        raise ValueError(f"일정 조립에서 지원하지 않는 이동수단입니다: {request.transport.value}")

    rule = request.pace_rule or PACE[request.pace.value]
    remaining = list(scored)
    budget = _TmapBudget(request.transport, get_route)
    days: list[ItineraryDay] = []

    for route_date in _dates(start_at.date(), end_at.date()):
        budget.start_day()
        day = _day_context(route_date, rule, start_at, end_at, request)
        state = _DayBuildState(
            current_coord=day.start_anchor.coord if day.start_anchor else request.start_coord,
            current_time=day.day_start,
        )

        while (
            remaining
            and state.slot_count < day.places_per_day
            and state.current_time < day.day_end
        ):
            meal = _meal_slot_for(day, state)
            ctx = _slot_context(day, state, meal)
            choice = best_candidate_with_diversity(
                remaining,
                state.rejected_today,
                ctx,
                state.items,
                enforce_diversity=not meal.is_meal,
            )
            # 낮 일정이 부족하거나 식사 시간이 오면 필요한 식사를 우선 배치한다.
            if (
                choice is None
                and not meal.is_meal
                and not state.meal_unfilled
                and (day.dinner_required or day.lunch_required)
            ):
                meal = _forced_meal_slot(day)
                ctx = _slot_context(day, state, meal)
                choice = best_candidate_with_diversity(
                    remaining, state.rejected_today, ctx, state.items, enforce_diversity=False
                )
            if choice is None:
                # 필요한 식사를 확실·확인 필요 후보로도 못 채우면 빈 슬롯으로 남기되,
                # break 하지 않고 남은 시간에 관광 후보를 계속 배치한다.
                if meal.is_meal and not state.restaurant_scheduled and not state.meal_unfilled:
                    state.unfilled.append(meal_unfilled_slot(remaining, len(state.items)))
                    state.meal_unfilled = True
                    continue
                break

            if not _place_candidate(remaining, state, choice, ctx, meal, budget, day, request):
                continue
            if meal.is_dinner:
                break

        days.append(_finalize_day(remaining, state, day, budget, request))

    return Itinerary(tuple(days))


def _day_context(
    route_date: date,
    rule: PaceRule,
    start_at: datetime,
    end_at: datetime,
    request: BuildRequest,
) -> _DayContext:
    window_start, window_end = (_parse_time(value) for value in rule["window"])
    day_start = max(datetime.combine(route_date, window_start, KST), start_at)
    day_end = min(datetime.combine(route_date, window_end, KST), end_at)
    # plan_day 가 그날의 슬롯 구성(활동/식사 개수·환경 선호)을 정한다.
    day_slots = plan_day(
        day_start,
        day_end,
        rule,
        request.day_forecasts.get(route_date),
        restaurant_preferred=request.restaurant_preferred,
        indoor_bias=request.indoor_bias,
    )
    activity_envs = [
        (slot.env_preference, slot.avoid_outdoor_midday)
        for slot in day_slots
        if slot.kind == "activity"
    ]
    meal_plan = next((slot for slot in day_slots if slot.kind in ("dinner", "lunch")), None)
    end_anchor = request.day_end_anchors.get(route_date)
    return _DayContext(
        route_date=route_date,
        day_start=day_start,
        day_end=day_end,
        dinner_start=datetime.combine(route_date, DINNER_START, KST),
        dinner_start_by=datetime.combine(route_date, DINNER_START_BY, KST),
        lunch_start=datetime.combine(route_date, LUNCH_START, KST),
        lunch_start_by=datetime.combine(route_date, LUNCH_START_BY, KST),
        places_per_day=len(day_slots),
        dinner_required=meal_plan is not None and meal_plan.kind == "dinner",
        lunch_required=meal_plan is not None and meal_plan.kind == "lunch",
        activity_envs=activity_envs,
        end_coord=end_anchor.coord if end_anchor else None,
        start_anchor=request.day_start_anchors.get(route_date),
        end_anchor=end_anchor,
        rule=rule,
        transport=request.transport,
    )


def _meal_slot_for(day: _DayContext, state: _DayBuildState) -> _MealSlot:
    """이번 슬롯의 식사 트리거(개수·시각)와 그에 따른 제약을 정한다."""
    # 마지막 남은 한 슬롯은 식사용으로 남긴다(개수 기반 트리거).
    last_slot = state.slot_count == day.places_per_day - 1
    dinner_slot = (
        day.dinner_required
        and not state.meal_unfilled
        and (last_slot or state.current_time >= day.dinner_start)
    )
    lunch_slot = (
        day.lunch_required
        and not state.restaurant_scheduled
        and not state.meal_unfilled
        and (state.current_time >= day.lunch_start or last_slot)
    )
    is_meal = dinner_slot or lunch_slot
    blocked_types: set[ScheduleItemType] = (
        {ScheduleItemType.CAFE}
        if any(item.candidate.item_type == ScheduleItemType.CAFE for item in state.items)
        else set()
    )
    if not is_meal or state.restaurant_scheduled or state.meal_unfilled:
        blocked_types.add(ScheduleItemType.RESTAURANT)
    not_before = day.dinner_start if dinner_slot else day.lunch_start if lunch_slot else None
    start_by = day.dinner_start_by if dinner_slot else day.lunch_start_by if lunch_slot else None
    # 식사 전 관광 일정이 식사 시작 시각을 침범하지 않게 슬롯을 미리 비워둔다.
    visit_deadline = day.day_end
    reserve_meal = not state.restaurant_scheduled and not state.meal_unfilled and not is_meal
    if day.dinner_required and reserve_meal:
        visit_deadline = min(visit_deadline, day.dinner_start)
    elif day.lunch_required and reserve_meal:
        visit_deadline = min(visit_deadline, day.lunch_start)
    return _MealSlot(
        is_meal=is_meal,
        is_dinner=dinner_slot,
        not_before=not_before,
        start_by=start_by,
        visit_deadline=visit_deadline,
        blocked_types=frozenset(blocked_types),
        required_type=ScheduleItemType.RESTAURANT if is_meal else None,
    )


def _forced_meal_slot(day: _DayContext) -> _MealSlot:
    """활동을 못 채웠을 때 당겨 채우는 강제 식사 슬롯(제약 없이 식당만)."""
    dinner = day.dinner_required
    return _MealSlot(
        is_meal=True,
        is_dinner=dinner,
        not_before=day.dinner_start if dinner else day.lunch_start,
        start_by=day.dinner_start_by if dinner else day.lunch_start_by,
        visit_deadline=day.day_end,
        blocked_types=frozenset(),
        required_type=ScheduleItemType.RESTAURANT,
    )


def _slot_context(day: _DayContext, state: _DayBuildState, meal: _MealSlot) -> SlotSearchContext:
    """식사 결정과 활동 슬롯 환경 속성을 합쳐 후보 탐색 조건을 만든다."""
    env_preference: PlaceEnvironment | None = None
    avoid_outdoor_midday = False
    if not meal.is_meal and state.activities_placed < len(day.activity_envs):
        env_preference, avoid_outdoor_midday = day.activity_envs[state.activities_placed]
    return SlotSearchContext(
        current_coord=state.current_coord,
        current_time=state.current_time,
        day_end=meal.visit_deadline,
        transport=day.transport,
        rest_min=day.rule["rest_min"] if state.items else 0,
        end_coord=day.end_coord,
        not_before=meal.not_before,
        start_by=meal.start_by,
        required_type=meal.required_type,
        blocked_types=meal.blocked_types,
        max_travel_min=day.rule["max_travel_min"],
        env_preference=env_preference,
        avoid_outdoor_midday=avoid_outdoor_midday,
    )


def _place_candidate(
    remaining: list[ScoredCandidate],
    state: _DayBuildState,
    choice: ScoredCandidate,
    ctx: SlotSearchContext,
    meal: _MealSlot,
    budget: _TmapBudget,
    day: _DayContext,
    request: BuildRequest,
) -> bool:
    """선택된 후보의 실제 경로·방문 시각을 확정해 배치한다. 시간 불가면 거절(False)."""
    depart_at = state.current_time + timedelta(minutes=ctx.rest_min)
    route = budget.leg(state.current_coord, (choice.lat, choice.lng), depart_at, day.route_date)
    arrival = depart_at + timedelta(minutes=route.duration_min)
    visit = fit_visit(
        choice,
        max(arrival, meal.not_before) if meal.not_before is not None else arrival,
        meal.visit_deadline,
    )
    if visit is None or (meal.start_by is not None and visit[0] > meal.start_by):
        state.rejected_today.add(choice.place_id)
        return False

    starts_at, ends_at = visit
    if state.items or day.start_anchor:
        state.moves.append(ScheduledMove(transport=request.transport, route=route))
    remaining.remove(choice)
    # 같은 슬롯 제약으로 다른 후보 최대 3개(확인 필요 포함)를 대안으로 남긴다.
    state.alternatives[choice.place_id] = tuple(
        top_alternatives(remaining, state.rejected_today, ctx)
    )
    state.items.append(ScheduledItem(candidate=choice, starts_at=starts_at, ends_at=ends_at))
    state.current_coord = (choice.lat, choice.lng)
    state.current_time = ends_at
    if not meal.is_meal:
        state.activities_placed += 1
    state.restaurant_scheduled = state.restaurant_scheduled or (
        choice.item_type == ScheduleItemType.RESTAURANT
    )
    return True


def _finalize_day(
    remaining: list[ScoredCandidate],
    state: _DayBuildState,
    day: _DayContext,
    budget: _TmapBudget,
    request: BuildRequest,
) -> ItineraryDay:
    """루프가 끝난 뒤 식사 안전망·앵커·숙소 복귀 이동을 마무리하고 하루를 만든다."""
    # 어떤 경로로 루프가 끝났든(시간 초과·후보 소진) 필요한 식사가 안 채워졌으면
    # 빈 슬롯을 남긴다. 이중 기록은 meal_unfilled 로 막는다.
    if (
        (day.dinner_required or day.lunch_required)
        and not state.restaurant_scheduled
        and not state.meal_unfilled
    ):
        state.unfilled.append(meal_unfilled_slot(remaining, len(state.items)))
        state.meal_unfilled = True

    # 방문이든 빈 슬롯이든 내용이 있으면 앵커를 남긴다(빈 슬롯만 있는 날도 출발지·숙소 저장).
    has_content = bool(state.items) or bool(state.unfilled)
    end_arrival = None
    if has_content and day.end_anchor is not None and (state.items or day.start_anchor):
        return_route = budget.leg(
            state.current_coord, day.end_anchor.coord, state.current_time, day.route_date
        )
        state.moves.append(ScheduledMove(transport=request.transport, route=return_route))
        end_arrival = state.current_time + timedelta(minutes=return_route.duration_min)

    return ItineraryDay(
        day.route_date,
        tuple(state.items),
        tuple(state.moves),
        dinner_required=day.dinner_required,
        restaurant_required=day.dinner_required or day.lunch_required,
        start_anchor=day.start_anchor if has_content else None,
        end_anchor=day.end_anchor if has_content else None,
        day_start=day.day_start if has_content and day.start_anchor else None,
        end_arrival=end_arrival,
        unfilled=tuple(state.unfilled),
        alternatives=state.alternatives,
    )


def _as_kst(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("여행 시각에는 시간대 정보가 필요합니다")
    return value.astimezone(KST)


def _parse_time(value: str) -> time:
    return time.fromisoformat(value)


def _dates(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)
