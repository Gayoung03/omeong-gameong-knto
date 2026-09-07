"""점수화된 후보 중 슬롯 제약(시간·동선·다양성·등급)에 맞는 최선을 고른다.

한 슬롯을 채울 때의 고정 조건은 SlotSearchContext 로 묶고, 후보가 부족할 때
규칙을 한 단계씩 푸는 완화 사다리는 Rung 의 나열로 표현한다.
"""

import math
import uuid
from collections import Counter
from dataclasses import dataclass, field, replace
from datetime import datetime, time, timedelta

from app.db.models.enums import PlaceEnvironment, ScheduleItemType, TransportType
from app.recommend.schemas import CandidateTier, ScoredCandidate
from app.recommend.travel_estimate import estimate_leg

from .fit import fit_visit
from .types import (
    KST,
    MAX_ALTERNATIVES,
    UNFILLED_MEAL_REASON,
    Coordinate,
    ScheduledItem,
    UnfilledSlot,
)

# 더위 회피가 걸리는 낮 시간대(정오~오후 3시).
_MIDDAY_START = time(12)
_MIDDAY_END = time(15)

# 후보 등급 사다리: 먼저 확실(VERIFIED)만, 끝내 못 채우면 확인 필요(NEEDS_CHECK)까지 허용.
VERIFIED_ONLY = frozenset({CandidateTier.VERIFIED})
ANY_TIER = frozenset({CandidateTier.VERIFIED, CandidateTier.NEEDS_CHECK})

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
class SlotSearchContext:
    """한 슬롯을 채울 때 완화와 무관하게 고정되는 조건."""

    current_coord: Coordinate
    current_time: datetime
    day_end: datetime
    transport: TransportType
    rest_min: int
    end_coord: Coordinate | None
    not_before: datetime | None = None
    start_by: datetime | None = None
    required_type: ScheduleItemType | None = None
    blocked_types: frozenset[ScheduleItemType] = frozenset()
    # 차멀미 반려동물이 있을 때의 구간 이동시간 상한. 완화 사다리가 풀 수 있다.
    max_travel_min: int | None = None
    # 날씨 하루 구성 규칙(plan_day). env_preference=INDOOR 면 비 예보라 실외를 피하고,
    # avoid_outdoor_midday 면 더위라 방문이 정오~15시에 걸치는 실외를 피한다. 둘 다
    # 완화 사다리의 "환경 선호 해제" 단계에서 풀린다.
    env_preference: PlaceEnvironment | None = None
    avoid_outdoor_midday: bool = False
    # 다양성 일일 한도 판정에 쓰는, 지금까지 채운 그룹별 개수.
    diversity_group_counts: Counter[str] = field(default_factory=Counter)


@dataclass(frozen=True)
class Rung:
    """완화 사다리의 한 단계. 아래로 갈수록 제약을 하나씩 푼다."""

    blocked_groups: frozenset[str]
    enforce_daily_limits: bool
    allowed_tiers: frozenset[CandidateTier]
    travel_limit: int | None
    apply_env: bool = True


def best_candidate_with_diversity(
    candidates: list[ScoredCandidate],
    rejected: set[uuid.UUID],
    ctx: SlotSearchContext,
    items: list[ScheduledItem],
    *,
    enforce_diversity: bool,
) -> ScoredCandidate | None:
    """다양성 규칙을 우선하되 후보 부족이 전체 일정 실패로 이어지지 않게 완화한다."""

    if not enforce_diversity:
        # 환경 선호 준수 → 환경 해제 → 이동 상한 해제 → 확인 필요 허용 순으로 완화한다.
        rungs = (
            Rung(frozenset(), False, VERIFIED_ONLY, ctx.max_travel_min, apply_env=True),
            Rung(frozenset(), False, VERIFIED_ONLY, ctx.max_travel_min, apply_env=False),
            Rung(frozenset(), False, VERIFIED_ONLY, None, apply_env=False),
            Rung(frozenset(), False, ANY_TIER, None, apply_env=False),
        )
        return _first_match(candidates, rejected, ctx, rungs)

    group_counts = Counter(_diversity_group(item.candidate) for item in items)
    blocked = frozenset({_diversity_group(items[-1].candidate)}) if items else frozenset()
    ctx = replace(ctx, diversity_group_counts=group_counts)
    # 다양성 완화 → 환경 선호 해제 → 이동시간 상한 해제 → 확인 필요 허용 순으로 내려간다.
    rungs = (
        Rung(blocked, True, VERIFIED_ONLY, ctx.max_travel_min, apply_env=True),
        Rung(frozenset(), True, VERIFIED_ONLY, ctx.max_travel_min, apply_env=True),
        Rung(frozenset(), False, VERIFIED_ONLY, ctx.max_travel_min, apply_env=True),
        Rung(frozenset(), False, VERIFIED_ONLY, ctx.max_travel_min, apply_env=False),
        Rung(frozenset(), False, VERIFIED_ONLY, None, apply_env=False),
        Rung(frozenset(), False, ANY_TIER, None, apply_env=False),
    )
    return _first_match(candidates, rejected, ctx, rungs)


def _first_match(
    candidates: list[ScoredCandidate],
    rejected: set[uuid.UUID],
    ctx: SlotSearchContext,
    rungs: tuple[Rung, ...],
) -> ScoredCandidate | None:
    for rung in rungs:
        choice = _best_candidate(candidates, rejected, ctx, rung)
        if choice is not None:
            return choice
    return None


def _best_candidate(
    candidates: list[ScoredCandidate],
    rejected: set[uuid.UUID],
    ctx: SlotSearchContext,
    rung: Rung,
) -> ScoredCandidate | None:
    choices: list[tuple[float, float, ScoredCandidate]] = []
    for candidate in candidates:
        diversity_group = _diversity_group(candidate)
        if (
            candidate.place_id in rejected
            or candidate.tier not in rung.allowed_tiers
            or candidate.item_type in ctx.blocked_types
            or (ctx.required_type is not None and candidate.item_type != ctx.required_type)
            or diversity_group in rung.blocked_groups
            or (
                rung.enforce_daily_limits
                and ctx.diversity_group_counts[diversity_group]
                >= DAILY_DIVERSITY_LIMITS.get(diversity_group, math.inf)
            )
        ):
            continue
        travel_min = estimate_leg(
            ctx.current_coord, (candidate.lat, candidate.lng), ctx.transport
        ).duration_min
        # 차멀미 반려동물이 있으면 긴 구간을 뺀다. 완화 사다리가 상한을 풀 수 있다.
        if rung.travel_limit is not None and travel_min > rung.travel_limit:
            continue
        return_min = (
            estimate_leg((candidate.lat, candidate.lng), ctx.end_coord, ctx.transport).duration_min
            if ctx.end_coord is not None
            else 0
        )
        # 그날 마지막 숙소 복귀 구간도 같은 상한으로 거른다(가장 피곤한 구간).
        if rung.travel_limit is not None and return_min > rung.travel_limit:
            continue
        arrival = ctx.current_time + timedelta(minutes=ctx.rest_min + travel_min)
        visit = fit_visit(
            candidate,
            max(arrival, ctx.not_before) if ctx.not_before is not None else arrival,
            ctx.day_end - timedelta(minutes=return_min),
        )
        if visit is None:
            continue
        if ctx.start_by is not None and visit[0] > ctx.start_by:
            continue
        if rung.apply_env and candidate.environment == PlaceEnvironment.OUTDOOR and (
            ctx.env_preference == PlaceEnvironment.INDOOR
            or (ctx.avoid_outdoor_midday and _overlaps_midday(visit[0], visit[1]))
        ):
            continue
        cost = ctx.rest_min + travel_min + candidate.average_stay_minutes
        choices.append((candidate.total_score / max(cost, 1), candidate.total_score, candidate))

    return max(choices, key=lambda choice: choice[:2])[2] if choices else None


def top_alternatives(
    candidates: list[ScoredCandidate],
    rejected: set[uuid.UUID],
    ctx: SlotSearchContext,
    limit: int = MAX_ALTERNATIVES,
) -> list[ScoredCandidate]:
    """선택된 항목과 같은 슬롯 제약으로 갈 만한 다른 후보(확인 필요 포함) 최대 limit개.

    이미 쓰인 곳은 candidates(remaining)에서 빠져 있고, 선택된 것도 호출 전에 제거된다.
    다양성 제약·이동 상한은 걸지 않는다 — "이 자리 대신 갈 곳"이라 같은 유형이어도 무방하다.
    """
    excluded = set(rejected)
    rung = Rung(frozenset(), False, ANY_TIER, None, apply_env=False)
    alternatives: list[ScoredCandidate] = []
    for _ in range(limit):
        alternative = _best_candidate(candidates, excluded, ctx, rung)
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


def meal_unfilled_slot(candidates: list[ScoredCandidate], position: int) -> UnfilledSlot:
    """못 채운 식사 슬롯 하나. 확인 필요 식당 후보를 상위 3개까지 붙인다."""
    return UnfilledSlot(
        item_type=ScheduleItemType.RESTAURANT,
        position=position,
        reason=UNFILLED_MEAL_REASON,
        candidates=tuple(_unfilled_candidates(candidates, ScheduleItemType.RESTAURANT)),
    )


def _overlaps_midday(starts_at: datetime, ends_at: datetime) -> bool:
    """방문 구간이 더위 회피 시간대(정오~15시)와 겹치는가."""
    midday_start = datetime.combine(starts_at.date(), _MIDDAY_START, KST)
    midday_end = datetime.combine(starts_at.date(), _MIDDAY_END, KST)
    return starts_at < midday_end and ends_at > midday_start


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
