"""점수화된 장소를 시간 제약이 있는 일자별 일정으로 조립한다."""

import math
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.db.models.enums import ScheduleItemType, TransportType, TripPace
from app.recommend.common.geo import haversine_m
from app.recommend.config.pace import PACE
from app.recommend.schemas import BusinessHour, ScoredCandidate
from app.recommend.tmap import RouteLeg

KST = ZoneInfo("Asia/Seoul")
DINNER_START = time(17)
Coordinate = tuple[float, float]
RouteProvider = Callable[[Coordinate, Coordinate, TransportType, datetime | None], RouteLeg]

# 후보 비교 때마다 TMAP을 부르지 않기 위한 보수적인 평균 이동 속도다.
SPEED_METERS_PER_MINUTE = {
    TransportType.RENTAL_CAR: 500,
    TransportType.OWN_CAR: 500,
    TransportType.TAXI: 500,
    TransportType.WALK: 75,
}
SUPPORTED_TRANSPORTS = frozenset(SPEED_METERS_PER_MINUTE)


@dataclass(frozen=True)
class BuildRequest:
    start_at: datetime
    end_at: datetime
    pace: TripPace
    transport: TransportType
    start_coord: Coordinate
    day_start_anchors: dict[date, "RouteAnchor"] = field(default_factory=dict)
    day_end_anchors: dict[date, "RouteAnchor"] = field(default_factory=dict)


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
class ItineraryDay:
    route_date: date
    items: tuple[ScheduledItem, ...]
    moves: tuple[ScheduledMove, ...]
    dinner_required: bool
    start_anchor: RouteAnchor | None = None
    end_anchor: RouteAnchor | None = None
    day_start: datetime | None = None
    end_arrival: datetime | None = None


@dataclass(frozen=True)
class Itinerary:
    days: tuple[ItineraryDay, ...]


def build(
    scored: list[ScoredCandidate], request: BuildRequest, get_route: RouteProvider
) -> Itinerary:
    """직선거리로 후보를 좁히고 선택한 구간만 실제 경로를 조회한다."""

    start_at = _as_kst(request.start_at)
    end_at = _as_kst(request.end_at)
    if end_at <= start_at:
        raise ValueError("여행 종료 시각은 시작 시각보다 늦어야 합니다")
    if request.transport not in SPEED_METERS_PER_MINUTE:
        raise ValueError(f"일정 조립에서 지원하지 않는 이동수단입니다: {request.transport.value}")

    rule = PACE[request.pace.value]
    remaining = list(scored)
    days: list[ItineraryDay] = []

    for route_date in _dates(start_at.date(), end_at.date()):
        window_start, window_end = (_parse_time(value) for value in rule["window"])
        day_start = max(datetime.combine(route_date, window_start, KST), start_at)
        day_end = min(datetime.combine(route_date, window_end, KST), end_at)
        items: list[ScheduledItem] = []
        moves: list[ScheduledMove] = []
        rejected_today: set[uuid.UUID] = set()
        start_anchor = request.day_start_anchors.get(route_date)
        end_anchor = request.day_end_anchors.get(route_date)
        current_coord = start_anchor.coord if start_anchor else request.start_coord
        current_time = day_start

        while remaining and len(items) < rule["places_per_day"] and current_time < day_end:
            dinner_slot = len(items) == rule["places_per_day"] - 1
            blocked_types = (
                {ScheduleItemType.CAFE}
                if any(item.candidate.item_type == ScheduleItemType.CAFE for item in items)
                else set()
            )
            if not dinner_slot:
                blocked_types.add(ScheduleItemType.RESTAURANT)
            not_before = datetime.combine(route_date, DINNER_START, KST) if dinner_slot else None
            choice = _best_candidate(
                remaining,
                rejected_today,
                blocked_types,
                ScheduleItemType.RESTAURANT if dinner_slot else None,
                not_before,
                current_coord,
                current_time,
                day_end,
                request.transport,
                rule["rest_min"] if items else 0,
                end_anchor.coord if end_anchor else None,
            )
            # 낮 일정이 부족해도 저녁 식사는 마지막 일정으로 시도한다.
            if choice is None and not dinner_slot:
                dinner_slot = True
                not_before = datetime.combine(route_date, DINNER_START, KST)
                choice = _best_candidate(
                    remaining,
                    rejected_today,
                    set(),
                    ScheduleItemType.RESTAURANT,
                    not_before,
                    current_coord,
                    current_time,
                    day_end,
                    request.transport,
                    rule["rest_min"] if items else 0,
                    end_anchor.coord if end_anchor else None,
                )
            if choice is None:
                break

            rest_min = rule["rest_min"] if items else 0
            depart_at = current_time + timedelta(minutes=rest_min)
            route = get_route(
                current_coord,
                (choice.lat, choice.lng),
                request.transport,
                depart_at,
            )
            arrival = depart_at + timedelta(minutes=route.duration_min)
            visit = _fit_visit(
                choice,
                max(arrival, not_before) if not_before is not None else arrival,
                day_end,
            )
            if visit is None:
                rejected_today.add(choice.place_id)
                continue

            starts_at, ends_at = visit
            if items or start_anchor:
                moves.append(
                    ScheduledMove(
                        transport=request.transport,
                        route=route,
                    )
                )
            items.append(ScheduledItem(candidate=choice, starts_at=starts_at, ends_at=ends_at))
            remaining.remove(choice)
            current_coord = (choice.lat, choice.lng)
            current_time = ends_at
            if dinner_slot:
                break

        end_arrival = None
        if items and end_anchor is not None:
            return_route = get_route(
                current_coord,
                end_anchor.coord,
                request.transport,
                current_time,
            )
            moves.append(ScheduledMove(transport=request.transport, route=return_route))
            end_arrival = current_time + timedelta(minutes=return_route.duration_min)

        days.append(
            ItineraryDay(
                route_date,
                tuple(items),
                tuple(moves),
                dinner_required=day_end.time() >= DINNER_START,
                start_anchor=start_anchor if items else None,
                end_anchor=end_anchor if items else None,
                day_start=day_start if items and start_anchor else None,
                end_arrival=end_arrival,
            )
        )

    return Itinerary(tuple(days))


def _best_candidate(
    candidates: list[ScoredCandidate],
    rejected: set[uuid.UUID],
    blocked_types: set[ScheduleItemType],
    required_type: ScheduleItemType | None,
    not_before: datetime | None,
    current_coord: Coordinate,
    current_time: datetime,
    day_end: datetime,
    transport: TransportType,
    rest_min: int,
    end_coord: Coordinate | None,
) -> ScoredCandidate | None:
    choices: list[tuple[float, float, ScoredCandidate]] = []
    for candidate in candidates:
        if (
            candidate.place_id in rejected
            or candidate.item_type in blocked_types
            or (required_type is not None and candidate.item_type != required_type)
        ):
            continue
        travel_min = math.ceil(
            haversine_m(current_coord, (candidate.lat, candidate.lng))
            / SPEED_METERS_PER_MINUTE[transport]
        )
        return_min = (
            math.ceil(
                haversine_m((candidate.lat, candidate.lng), end_coord)
                / SPEED_METERS_PER_MINUTE[transport]
            )
            if end_coord is not None
            else 0
        )
        visit = _fit_visit(
            candidate,
            max(current_time + timedelta(minutes=rest_min + travel_min), not_before)
            if not_before is not None
            else current_time + timedelta(minutes=rest_min + travel_min),
            day_end - timedelta(minutes=return_min),
        )
        if visit is None:
            continue
        cost = rest_min + travel_min + candidate.average_stay_minutes
        choices.append((candidate.total_score / max(cost, 1), candidate.total_score, candidate))

    return max(choices, key=lambda choice: choice[:2])[2] if choices else None


def _fit_visit(
    candidate: ScoredCandidate, arrival: datetime, day_end: datetime
) -> tuple[datetime, datetime] | None:
    hours = _hours_for(candidate, arrival.date())
    if hours is not None and hours.is_closed:
        return None

    starts_at = arrival
    closes_at = day_end
    if hours is not None and hours.opens_at is not None and hours.closes_at is not None:
        starts_at = max(starts_at, datetime.combine(arrival.date(), hours.opens_at, KST))
        closes_at = min(closes_at, datetime.combine(arrival.date(), hours.closes_at, KST))

    duration = timedelta(minutes=candidate.average_stay_minutes)
    if hours is not None and hours.break_start_at is not None and hours.break_end_at is not None:
        break_start = datetime.combine(arrival.date(), hours.break_start_at, KST)
        break_end = datetime.combine(arrival.date(), hours.break_end_at, KST)
        if starts_at < break_end and starts_at + duration > break_start:
            starts_at = break_end

    ends_at = starts_at + duration
    return (starts_at, ends_at) if ends_at <= closes_at else None


def _hours_for(candidate: ScoredCandidate, route_date: date) -> BusinessHour | None:
    # Python은 월요일=0, 추천 계약은 일요일=0이다.
    day_of_week = (route_date.weekday() + 1) % 7
    return next(
        (hour for hour in candidate.business_hours if hour.day_of_week == day_of_week), None
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
