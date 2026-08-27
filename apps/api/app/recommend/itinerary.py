"""점수화된 장소를 시간 제약이 있는 일자별 일정으로 조립한다."""

import math
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.db.models.enums import TransportType, TripPace
from app.recommend.common.geo import haversine_m
from app.recommend.config.pace import PACE
from app.recommend.schemas import BusinessHour, ScoredCandidate
from app.recommend.tmap import RouteLeg

KST = ZoneInfo("Asia/Seoul")
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
    day_start_coords: dict[date, Coordinate] = field(default_factory=dict)


@dataclass(frozen=True)
class ScheduledItem:
    candidate: ScoredCandidate
    starts_at: datetime
    ends_at: datetime


@dataclass(frozen=True)
class ScheduledMove:
    from_place_id: uuid.UUID
    to_place_id: uuid.UUID
    transport: TransportType
    route: RouteLeg


@dataclass(frozen=True)
class ItineraryDay:
    route_date: date
    items: tuple[ScheduledItem, ...]
    moves: tuple[ScheduledMove, ...]


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
        current_coord = request.day_start_coords.get(route_date, request.start_coord)
        current_time = day_start

        while remaining and len(items) < rule["places_per_day"] and current_time < day_end:
            choice = _best_candidate(
                remaining,
                rejected_today,
                current_coord,
                current_time,
                day_end,
                request.transport,
                rule["rest_min"] if items else 0,
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
            visit = _fit_visit(choice, depart_at + timedelta(minutes=route.duration_min), day_end)
            if visit is None:
                rejected_today.add(choice.place_id)
                continue

            starts_at, ends_at = visit
            if items:
                moves.append(
                    ScheduledMove(
                        from_place_id=items[-1].candidate.place_id,
                        to_place_id=choice.place_id,
                        transport=request.transport,
                        route=route,
                    )
                )
            items.append(ScheduledItem(candidate=choice, starts_at=starts_at, ends_at=ends_at))
            remaining.remove(choice)
            current_coord = (choice.lat, choice.lng)
            current_time = ends_at

        days.append(ItineraryDay(route_date, tuple(items), tuple(moves)))

    return Itinerary(tuple(days))


def _best_candidate(
    candidates: list[ScoredCandidate],
    rejected: set[uuid.UUID],
    current_coord: Coordinate,
    current_time: datetime,
    day_end: datetime,
    transport: TransportType,
    rest_min: int,
) -> ScoredCandidate | None:
    choices: list[tuple[float, float, ScoredCandidate]] = []
    for candidate in candidates:
        if candidate.place_id in rejected:
            continue
        travel_min = math.ceil(
            haversine_m(current_coord, (candidate.lat, candidate.lng))
            / SPEED_METERS_PER_MINUTE[transport]
        )
        visit = _fit_visit(
            candidate,
            current_time + timedelta(minutes=rest_min + travel_min),
            day_end,
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
