"""점수화된 장소를 시간 제약이 있는 일자별 일정으로 조립한다."""

import logging
import uuid
from datetime import date, datetime, time, timedelta

from app.db.models.enums import ScheduleItemType
from app.recommend.config.pace import PACE
from app.recommend.schemas import ScoredCandidate
from app.recommend.tmap import RouteLeg, TMapError
from app.recommend.travel_estimate import SUPPORTED_TRANSPORTS, estimate_leg

from .fit import fit_visit
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
    RouteProvider,
    ScheduledItem,
    ScheduledMove,
    UnfilledSlot,
)

logger = logging.getLogger(__name__)


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
    days: list[ItineraryDay] = []
    # TMAP 이 한 번 오류를 내면 여행 전체에 대해 실제 호출을 끈다. 타임아웃 10초짜리
    # 오류를 날마다 상한(12)만큼 반복하면 3분 폴링을 넘기므로 첫 오류에서 바로 끈다.
    tmap_available = True

    for route_date in _dates(start_at.date(), end_at.date()):
        window_start, window_end = (_parse_time(value) for value in rule["window"])
        day_start = max(datetime.combine(route_date, window_start, KST), start_at)
        day_end = min(datetime.combine(route_date, window_end, KST), end_at)
        items: list[ScheduledItem] = []
        moves: list[ScheduledMove] = []
        unfilled: list[UnfilledSlot] = []
        alternatives: dict[uuid.UUID, tuple[ScoredCandidate, ...]] = {}
        rejected_today: set[uuid.UUID] = set()
        route_calls = 0
        cap_logged = False

        def fetch_leg(
            origin: Coordinate,
            destination: Coordinate,
            depart_at: datetime,
            day: date = route_date,
        ) -> RouteLeg:
            """상한 이내·TMAP 정상일 때는 실제 경로를, 그 외에는 직선거리 추정을 돌려준다."""
            nonlocal route_calls, cap_logged, tmap_available
            if tmap_available and route_calls >= MAX_TMAP_CALLS_PER_DAY:
                if not cap_logged:
                    logger.warning(
                        "TMAP 호출 상한(%d) 도달 — %s 이후 구간은 직선거리로 추정합니다",
                        MAX_TMAP_CALLS_PER_DAY,
                        day,
                    )
                    cap_logged = True
            if not tmap_available or route_calls >= MAX_TMAP_CALLS_PER_DAY:
                return estimate_leg(origin, destination, request.transport)
            try:
                leg = get_route(origin, destination, request.transport, depart_at)
            except TMapError:
                logger.warning(
                    "TMAP 조회 실패 — 이번 여행의 이후 구간은 직선거리로 추정합니다",
                    exc_info=True,
                )
                tmap_available = False
                return estimate_leg(origin, destination, request.transport)
            # 캐시 적중·추정은 상한에서 제외하고 실제 TMAP 호출만 센다.
            if leg.source == "tmap":
                route_calls += 1
            return leg

        start_anchor = request.day_start_anchors.get(route_date)
        end_anchor = request.day_end_anchors.get(route_date)
        end_coord = end_anchor.coord if end_anchor else None
        current_coord = start_anchor.coord if start_anchor else request.start_coord
        current_time = day_start
        dinner_required = day_end.time() >= DINNER_START
        lunch_start = datetime.combine(route_date, LUNCH_START, KST)
        lunch_start_by = datetime.combine(route_date, LUNCH_START_BY, KST)
        lunch_required = (
            request.restaurant_preferred
            and not dinner_required
            and day_start <= lunch_start_by
            and day_end >= lunch_start
        )
        restaurant_scheduled = False
        # 필요한 식사를 빈 슬롯으로 처리했으면 True. 이후엔 식사 슬롯을 다시 시도하지 않고
        # 남은 시간에 관광 후보를 계속 배치한다(빈 슬롯이 슬롯 개수를 하나 차지한다).
        meal_unfilled = False

        while (
            remaining
            and len(items) + len(unfilled) < rule["places_per_day"]
            and current_time < day_end
        ):
            dinner_start = datetime.combine(route_date, DINNER_START, KST)
            dinner_start_by = datetime.combine(route_date, DINNER_START_BY, KST)
            # 마지막 남은 한 슬롯은 식사용으로 남긴다(개수 기반 트리거).
            last_slot = len(items) + len(unfilled) == rule["places_per_day"] - 1
            dinner_slot = (
                dinner_required
                and not meal_unfilled
                and (last_slot or current_time >= dinner_start)
            )
            lunch_slot = (
                lunch_required
                and not restaurant_scheduled
                and not meal_unfilled
                and (current_time >= lunch_start or last_slot)
            )
            meal_slot = dinner_slot or lunch_slot
            blocked_types: set[ScheduleItemType] = (
                {ScheduleItemType.CAFE}
                if any(item.candidate.item_type == ScheduleItemType.CAFE for item in items)
                else set()
            )
            if not meal_slot or restaurant_scheduled or meal_unfilled:
                blocked_types.add(ScheduleItemType.RESTAURANT)
            not_before = dinner_start if dinner_slot else lunch_start if lunch_slot else None
            start_by = dinner_start_by if dinner_slot else lunch_start_by if lunch_slot else None
            # 식사 전 관광 일정이 식사 시작 시각을 침범하지 않게 슬롯을 미리 비워둔다.
            visit_deadline = day_end
            reserve_meal = not restaurant_scheduled and not meal_unfilled and not meal_slot
            if dinner_required and reserve_meal:
                visit_deadline = min(visit_deadline, dinner_start)
            elif lunch_required and reserve_meal:
                visit_deadline = min(visit_deadline, lunch_start)
            rest_min = rule["rest_min"] if items else 0
            ctx = SlotSearchContext(
                current_coord=current_coord,
                current_time=current_time,
                day_end=visit_deadline,
                transport=request.transport,
                rest_min=rest_min,
                end_coord=end_coord,
                not_before=not_before,
                start_by=start_by,
                required_type=ScheduleItemType.RESTAURANT if meal_slot else None,
                blocked_types=frozenset(blocked_types),
                max_travel_min=rule["max_travel_min"],
            )
            choice = best_candidate_with_diversity(
                remaining, rejected_today, ctx, items, enforce_diversity=not meal_slot
            )
            # 낮 일정이 부족하거나 식사 시간이 오면 필요한 식사를 우선 배치한다.
            if (
                choice is None
                and not meal_slot
                and not meal_unfilled
                and (dinner_required or lunch_required)
            ):
                dinner_slot = dinner_required
                lunch_slot = lunch_required and not dinner_required
                meal_slot = True
                not_before = dinner_start if dinner_slot else lunch_start
                start_by = dinner_start_by if dinner_slot else lunch_start_by
                visit_deadline = day_end
                ctx = SlotSearchContext(
                    current_coord=current_coord,
                    current_time=current_time,
                    day_end=day_end,
                    transport=request.transport,
                    rest_min=rest_min,
                    end_coord=end_coord,
                    not_before=not_before,
                    start_by=start_by,
                    required_type=ScheduleItemType.RESTAURANT,
                    blocked_types=frozenset(),
                    max_travel_min=rule["max_travel_min"],
                )
                choice = best_candidate_with_diversity(
                    remaining, rejected_today, ctx, items, enforce_diversity=False
                )
            if choice is None:
                # 필요한 식사를 확실·확인 필요 후보로도 못 채우면 빈 슬롯으로 남기되,
                # break 하지 않고 남은 시간에 관광 후보를 계속 배치한다.
                if meal_slot and not restaurant_scheduled and not meal_unfilled:
                    unfilled.append(meal_unfilled_slot(remaining, len(items)))
                    meal_unfilled = True
                    continue
                break

            depart_at = current_time + timedelta(minutes=rest_min)
            route = fetch_leg(current_coord, (choice.lat, choice.lng), depart_at)
            arrival = depart_at + timedelta(minutes=route.duration_min)
            visit = fit_visit(
                choice,
                max(arrival, not_before) if not_before is not None else arrival,
                visit_deadline,
            )
            if visit is None or (start_by is not None and visit[0] > start_by):
                rejected_today.add(choice.place_id)
                continue

            starts_at, ends_at = visit
            if items or start_anchor:
                moves.append(ScheduledMove(transport=request.transport, route=route))
            remaining.remove(choice)
            # 같은 슬롯 제약으로 다른 후보 최대 3개(확인 필요 포함)를 대안으로 남긴다.
            alternatives[choice.place_id] = tuple(
                top_alternatives(remaining, rejected_today, ctx)
            )
            items.append(ScheduledItem(candidate=choice, starts_at=starts_at, ends_at=ends_at))
            current_coord = (choice.lat, choice.lng)
            current_time = ends_at
            restaurant_scheduled = restaurant_scheduled or (
                choice.item_type == ScheduleItemType.RESTAURANT
            )
            if dinner_slot:
                break

        # 어떤 경로로 루프가 끝났든(시간 초과·후보 소진) 필요한 식사가 안 채워졌으면
        # 빈 슬롯을 남긴다. 이중 기록은 meal_unfilled 로 막는다.
        if (dinner_required or lunch_required) and not restaurant_scheduled and not meal_unfilled:
            unfilled.append(meal_unfilled_slot(remaining, len(items)))
            meal_unfilled = True

        # 방문이든 빈 슬롯이든 내용이 있으면 앵커를 남긴다(빈 슬롯만 있는 날도 출발지·숙소 저장).
        has_content = bool(items) or bool(unfilled)
        end_arrival = None
        if has_content and end_anchor is not None and (items or start_anchor):
            return_route = fetch_leg(current_coord, end_anchor.coord, current_time)
            moves.append(ScheduledMove(transport=request.transport, route=return_route))
            end_arrival = current_time + timedelta(minutes=return_route.duration_min)

        days.append(
            ItineraryDay(
                route_date,
                tuple(items),
                tuple(moves),
                dinner_required=dinner_required,
                restaurant_required=dinner_required or lunch_required,
                start_anchor=start_anchor if has_content else None,
                end_anchor=end_anchor if has_content else None,
                day_start=day_start if has_content and start_anchor else None,
                end_arrival=end_arrival,
                unfilled=tuple(unfilled),
                alternatives=alternatives,
            )
        )

    return Itinerary(tuple(days))


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
