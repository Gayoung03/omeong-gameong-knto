"""점수화된 장소를 시간 제약이 있는 일자별 일정으로 조립한다."""

import logging
import math
import uuid
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.db.models.enums import ScheduleItemType, TransportType, TripPace
from app.recommend.config.pace import PACE
from app.recommend.schemas import BusinessHour, CandidateTier, ScoredCandidate
from app.recommend.tmap import RouteLeg, TMapError
from app.recommend.travel_estimate import SUPPORTED_TRANSPORTS, estimate_leg

logger = logging.getLogger(__name__)

KST = ZoneInfo("Asia/Seoul")
DINNER_START = time(17)
DINNER_START_BY = time(19, 30)
LUNCH_START = time(11, 30)
LUNCH_START_BY = time(14)
Coordinate = tuple[float, float]
RouteProvider = Callable[[Coordinate, Coordinate, TransportType, datetime | None], RouteLeg]

# 후보 등급 사다리: 먼저 확실(VERIFIED)만, 끝내 못 채우면 확인 필요(NEEDS_CHECK)까지 허용.
_VERIFIED_ONLY = frozenset({CandidateTier.VERIFIED})
_ANY_TIER = frozenset({CandidateTier.VERIFIED, CandidateTier.NEEDS_CHECK})
# 못 채운 식사 슬롯의 안내 문구(응답 recommendation_reason).
UNFILLED_MEAL_REASON = (
    "확실히 동반 가능한 식당을 찾지 못했어요. 아래 후보는 동반 여부 확인이 필요해요."
)
MAX_ALTERNATIVES = 3

# 후보가 계속 시간 제약에 안 맞으면 후보 수만큼 TMAP(타임아웃 10초)을 부를 수 있어
# 폴링 한도(3분)를 넘긴다. 하루당 호출을 이 상한으로 묶고, 초과분은 직선거리 추정으로
# 대체해 일정 조립을 계속 진행한다.
MAX_TMAP_CALLS_PER_DAY = 12

DIVERSITY_GROUP_BY_CATEGORY = {
    "beach": "coast",
    "oreum": "nature",
    "walking_trail": "nature",
    "rental_experience": "experience",
    "cafe": "cafe",
    "restaurant": "food",
    "restaurant_cafe": "food",
    "accommodation": "stay",
}
DAILY_DIVERSITY_LIMITS = {"coast": 1}


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

    rule = PACE[request.pace.value]
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

        while remaining and len(items) < rule["places_per_day"] and current_time < day_end:
            dinner_start = datetime.combine(route_date, DINNER_START, KST)
            dinner_start_by = datetime.combine(route_date, DINNER_START_BY, KST)
            dinner_slot = dinner_required and (
                len(items) == rule["places_per_day"] - 1 or current_time >= dinner_start
            )
            lunch_slot = lunch_required and not restaurant_scheduled and current_time >= lunch_start
            meal_slot = dinner_slot or lunch_slot
            blocked_types = (
                {ScheduleItemType.CAFE}
                if any(item.candidate.item_type == ScheduleItemType.CAFE for item in items)
                else set()
            )
            if not meal_slot or restaurant_scheduled:
                blocked_types.add(ScheduleItemType.RESTAURANT)
            not_before = dinner_start if dinner_slot else lunch_start if lunch_slot else None
            start_by = dinner_start_by if dinner_slot else lunch_start_by if lunch_slot else None
            # 식사 전 관광 일정이 식사 시작 시각을 침범하지 않게 슬롯을 미리 비워둔다.
            visit_deadline = day_end
            if dinner_required and not restaurant_scheduled and not meal_slot:
                visit_deadline = min(visit_deadline, dinner_start)
            elif lunch_required and not restaurant_scheduled and not meal_slot:
                visit_deadline = min(visit_deadline, lunch_start)
            choice = _best_candidate_with_diversity(
                remaining,
                rejected_today,
                blocked_types,
                ScheduleItemType.RESTAURANT if meal_slot else None,
                not_before,
                start_by,
                current_coord,
                current_time,
                visit_deadline,
                request.transport,
                rule["rest_min"] if items else 0,
                end_anchor.coord if end_anchor else None,
                items,
                enforce_diversity=not meal_slot,
            )
            # 낮 일정이 부족하거나 식사 시간이 오면 필요한 식사를 우선 배치한다.
            if choice is None and not meal_slot and (dinner_required or lunch_required):
                dinner_slot = dinner_required
                lunch_slot = lunch_required and not dinner_required
                meal_slot = True
                not_before = dinner_start if dinner_slot else lunch_start
                start_by = dinner_start_by if dinner_slot else lunch_start_by
                visit_deadline = day_end
                choice = _best_candidate_with_diversity(
                    remaining,
                    rejected_today,
                    set(),
                    ScheduleItemType.RESTAURANT,
                    not_before,
                    start_by,
                    current_coord,
                    current_time,
                    day_end,
                    request.transport,
                    rule["rest_min"] if items else 0,
                    end_anchor.coord if end_anchor else None,
                    items,
                    enforce_diversity=False,
                )
            if choice is None:
                # 필요한 식사 슬롯을 확실·확인 필요 후보로도 못 채우면 빈 슬롯으로 남긴다.
                if meal_slot and not restaurant_scheduled:
                    unfilled.append(
                        UnfilledSlot(
                            item_type=ScheduleItemType.RESTAURANT,
                            position=len(items),
                            reason=UNFILLED_MEAL_REASON,
                            candidates=tuple(
                                _unfilled_candidates(remaining, ScheduleItemType.RESTAURANT)
                            ),
                        )
                    )
                break

            rest_min = rule["rest_min"] if items else 0
            depart_at = current_time + timedelta(minutes=rest_min)
            route = fetch_leg(current_coord, (choice.lat, choice.lng), depart_at)
            arrival = depart_at + timedelta(minutes=route.duration_min)
            visit = _fit_visit(
                choice,
                max(arrival, not_before) if not_before is not None else arrival,
                visit_deadline,
            )
            if visit is None or (start_by is not None and visit[0] > start_by):
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
            remaining.remove(choice)
            # 같은 슬롯 제약으로 다른 후보 최대 3개(확인 필요 포함)를 대안으로 남긴다.
            alternatives[choice.place_id] = tuple(
                _top_alternatives(
                    remaining,
                    rejected_today,
                    blocked_types,
                    ScheduleItemType.RESTAURANT if meal_slot else None,
                    not_before,
                    start_by,
                    current_coord,
                    current_time,
                    visit_deadline,
                    request.transport,
                    rest_min,
                    end_anchor.coord if end_anchor else None,
                )
            )
            items.append(ScheduledItem(candidate=choice, starts_at=starts_at, ends_at=ends_at))
            current_coord = (choice.lat, choice.lng)
            current_time = ends_at
            restaurant_scheduled = restaurant_scheduled or (
                choice.item_type == ScheduleItemType.RESTAURANT
            )
            if dinner_slot:
                break

        end_arrival = None
        if items and end_anchor is not None:
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
                start_anchor=start_anchor if items else None,
                end_anchor=end_anchor if items else None,
                day_start=day_start if items and start_anchor else None,
                end_arrival=end_arrival,
                unfilled=tuple(unfilled),
                alternatives=alternatives,
            )
        )

    return Itinerary(tuple(days))


def _best_candidate_with_diversity(
    candidates: list[ScoredCandidate],
    rejected: set[uuid.UUID],
    blocked_types: set[ScheduleItemType],
    required_type: ScheduleItemType | None,
    not_before: datetime | None,
    start_by: datetime | None,
    current_coord: Coordinate,
    current_time: datetime,
    day_end: datetime,
    transport: TransportType,
    rest_min: int,
    end_coord: Coordinate | None,
    items: list[ScheduledItem],
    *,
    enforce_diversity: bool,
) -> ScoredCandidate | None:
    """다양성 규칙을 우선하되 후보 부족이 전체 일정 실패로 이어지지 않게 완화한다."""

    if not enforce_diversity:
        for allowed_tiers in (_VERIFIED_ONLY, _ANY_TIER):
            choice = _best_candidate(
                candidates,
                rejected,
                blocked_types,
                required_type,
                not_before,
                start_by,
                current_coord,
                current_time,
                day_end,
                transport,
                rest_min,
                end_coord,
                set(),
                Counter(),
                False,
                allowed_tiers,
            )
            if choice is not None:
                return choice
        return None

    group_counts = Counter(_diversity_group(item.candidate) for item in items)
    blocked_groups = {_diversity_group(items[-1].candidate)} if items else set()
    # 확실(VERIFIED) 후보로 다양성을 지키며 채우고, 끝내 없으면 마지막에 확인 필요까지 허용한다.
    attempts = (
        (blocked_groups, True, _VERIFIED_ONLY),
        (set(), True, _VERIFIED_ONLY),
        (set(), False, _VERIFIED_ONLY),
        (set(), False, _ANY_TIER),
    )
    for groups, enforce_daily_limits, allowed_tiers in attempts:
        choice = _best_candidate(
            candidates,
            rejected,
            blocked_types,
            required_type,
            not_before,
            start_by,
            current_coord,
            current_time,
            day_end,
            transport,
            rest_min,
            end_coord,
            groups,
            group_counts,
            enforce_daily_limits,
            allowed_tiers,
        )
        if choice is not None:
            return choice
    return None


def _best_candidate(
    candidates: list[ScoredCandidate],
    rejected: set[uuid.UUID],
    blocked_types: set[ScheduleItemType],
    required_type: ScheduleItemType | None,
    not_before: datetime | None,
    start_by: datetime | None,
    current_coord: Coordinate,
    current_time: datetime,
    day_end: datetime,
    transport: TransportType,
    rest_min: int,
    end_coord: Coordinate | None,
    blocked_diversity_groups: set[str],
    diversity_group_counts: Counter[str],
    enforce_daily_diversity_limits: bool,
    allowed_tiers: frozenset[CandidateTier] = _VERIFIED_ONLY,
) -> ScoredCandidate | None:
    choices: list[tuple[float, float, ScoredCandidate]] = []
    for candidate in candidates:
        diversity_group = _diversity_group(candidate)
        if (
            candidate.place_id in rejected
            or candidate.tier not in allowed_tiers
            or candidate.item_type in blocked_types
            or (required_type is not None and candidate.item_type != required_type)
            or diversity_group in blocked_diversity_groups
            or (
                enforce_daily_diversity_limits
                and diversity_group_counts[diversity_group]
                >= DAILY_DIVERSITY_LIMITS.get(diversity_group, math.inf)
            )
        ):
            continue
        travel_min = estimate_leg(
            current_coord, (candidate.lat, candidate.lng), transport
        ).duration_min
        return_min = (
            estimate_leg((candidate.lat, candidate.lng), end_coord, transport).duration_min
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
        if start_by is not None and visit[0] > start_by:
            continue
        cost = rest_min + travel_min + candidate.average_stay_minutes
        choices.append((candidate.total_score / max(cost, 1), candidate.total_score, candidate))

    return max(choices, key=lambda choice: choice[:2])[2] if choices else None


def _top_alternatives(
    candidates: list[ScoredCandidate],
    rejected: set[uuid.UUID],
    blocked_types: set[ScheduleItemType],
    required_type: ScheduleItemType | None,
    not_before: datetime | None,
    start_by: datetime | None,
    current_coord: Coordinate,
    current_time: datetime,
    day_end: datetime,
    transport: TransportType,
    rest_min: int,
    end_coord: Coordinate | None,
    limit: int = MAX_ALTERNATIVES,
) -> list[ScoredCandidate]:
    """선택된 항목과 같은 슬롯 제약으로 갈 만한 다른 후보(확인 필요 포함) 최대 limit개.

    이미 쓰인 곳은 candidates(remaining)에서 빠져 있고, 선택된 것도 호출 전에 제거된다.
    다양성 제약은 걸지 않는다 — "이 자리 대신 갈 곳"이라 같은 유형이어도 무방하다.
    """
    excluded = set(rejected)
    alternatives: list[ScoredCandidate] = []
    for _ in range(limit):
        alternative = _best_candidate(
            candidates,
            excluded,
            blocked_types,
            required_type,
            not_before,
            start_by,
            current_coord,
            current_time,
            day_end,
            transport,
            rest_min,
            end_coord,
            set(),
            Counter(),
            False,
            _ANY_TIER,
        )
        if alternative is None:
            break
        alternatives.append(alternative)
        excluded.add(alternative.place_id)
    return alternatives


def _unfilled_candidates(
    candidates: list[ScoredCandidate],
    required_type: ScheduleItemType,
    limit: int = MAX_ALTERNATIVES,
) -> list[ScoredCandidate]:
    """빈 슬롯에 붙일 "확인 필요" 후보. 시간·동선 적합과 무관하게 점수순 상위 limit개."""
    matches = [
        candidate
        for candidate in candidates
        if candidate.item_type == required_type and candidate.tier == CandidateTier.NEEDS_CHECK
    ]
    matches.sort(key=lambda candidate: (-candidate.total_score, candidate.place_id.int))
    return matches[:limit]


def _diversity_group(candidate: ScoredCandidate) -> str:
    """원본 카테고리와 표준 태그로 사용자가 체감하는 장소 유형을 복원한다."""

    category_group = DIVERSITY_GROUP_BY_CATEGORY.get(candidate.source_category or "")
    if category_group is not None:
        return category_group
    # candidate.tags 는 place_tags.code(영문)다.
    tags = set(candidate.tags)
    if "sea" in tags:
        return "coast"
    if tags & {"walk", "rest"}:
        return "nature"
    if "indoor_tourism" in tags:
        return "culture"
    if "experience" in tags:
        return "experience"
    return candidate.item_type.value


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
