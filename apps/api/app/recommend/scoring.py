"""2단계 추천 후보 점수화."""

from collections.abc import Sequence
from math import log1p

from pydantic import Field

from app.db.models.enums import PetPolicyType, PetSize, PlaceEnvironment, ScheduleItemType
from app.recommend.common.geo import haversine_m
from app.recommend.config.tags import STANDARD_TAG_SET
from app.recommend.config.weights import MAX_DAILY_DISTANCE_M
from app.recommend.schemas import (
    Candidate,
    PetPolicy,
    PetProfile,
    RecommendationSchema,
    ScoredCandidate,
    Weights,
)

SCORE_LABELS = {
    "preference": "이번 여행 선호",
    "pet": "반려 편의",
    "proximity": "기준점 근접도",
    "rating": "평점",
    "weather": "날씨 적합도",
    "popularity": "인기",
}

# 반려 적합도 계수(_fit_factor). 값 자체가 아니라 근거를 이름으로 남긴다.
#: 최대 허용 체중의 몇 % 를 넘으면 감점하는가(100% 초과는 필터에서 이미 제외).
WEIGHT_WARNING_RATIO = 0.7
#: 체중이 경고 구간(70~100%)일 때 곱하는 계수.
OVERWEIGHT_FIT = 0.85
#: 이동장 필수인데 대형/중형이라 현실성이 떨어질 때의 계수.
CARRIER_LARGE_FIT = 0.6
CARRIER_MEDIUM_FIT = 0.8
#: 입마개 필수가 대형에게 주는 부담 계수(소형은 영향 없음).
MUZZLE_LARGE_FIT = 0.9


class ScoringContext(RecommendationSchema):
    weights: Weights
    base_coord: tuple[float, float]
    additional_base_coords: tuple[tuple[float, float], ...] = ()
    preferred_tags: frozenset[str] = Field(default_factory=frozenset)
    precipitation_probability: int | None = Field(default=None, ge=0, le=100)
    max_daily_distance_m: float = Field(default=MAX_DAILY_DISTANCE_M, gt=0)
    pets: tuple[PetProfile, ...] = ()


def preference_score(
    user_tags: set[str],
    place_tags: set[str],
    item_type: ScheduleItemType | None = None,
) -> float:
    """표준 태그 집합의 Jaccard 유사도."""

    user = user_tags & STANDARD_TAG_SET
    place = place_tags & STANDARD_TAG_SET
    tag_score = len(user & place) / len(user | place) if user and place else 0.0
    category_score = 1.0 if item_type and f"category:{item_type.value}" in user_tags else 0.0
    return max(tag_score, category_score)


def rating_score(rating_avg: float | None) -> float:
    return 0.5 if rating_avg is None else _clamp((rating_avg - 1) / 4)


def proximity_score(
    base_coord: tuple[float, float],
    place_coord: tuple[float, float],
    max_daily_distance_m: float,
) -> float:
    return 1 - min(1.0, haversine_m(base_coord, place_coord) / max_daily_distance_m)


def weather_score(
    environment: PlaceEnvironment | None, precipitation_probability: int | None
) -> float:
    if environment is None or precipitation_probability is None:
        return 0.5
    precipitation = precipitation_probability / 100
    if environment == PlaceEnvironment.OUTDOOR:
        return 1 - precipitation
    if environment == PlaceEnvironment.INDOOR:
        return max(0.8, 1 - 0.3 * precipitation)
    return 1 - 0.5 * precipitation


def _fit_factor(policy: PetPolicy, pet: PetProfile) -> float:
    """한 반려동물의 정책 적합도 계수(≤1). 곱셈으로 합쳐 base 점수에 적용한다."""
    if policy.allowed_sizes and pet.size is not None and pet.size.value not in policy.allowed_sizes:
        return 0.0  # 필터에서 이미 BLOCKED 라 보통 없음
    factor = 1.0
    if (
        policy.max_weight_kg is not None
        and pet.weight_kg is not None
        and pet.weight_kg > policy.max_weight_kg * WEIGHT_WARNING_RATIO
    ):
        factor *= OVERWEIGHT_FIT
    if policy.carrier_required:
        if pet.size == PetSize.LARGE:
            factor *= CARRIER_LARGE_FIT  # 대형견을 안고 이동은 비현실적
        elif pet.size == PetSize.MEDIUM:
            factor *= CARRIER_MEDIUM_FIT
    if policy.muzzle_required and pet.size == PetSize.LARGE:
        factor *= MUZZLE_LARGE_FIT  # 소형은 영향 없음
    return factor


def pet_score(candidate: Candidate, pets: Sequence[PetProfile] = ()) -> float:
    """허용 범위·이용 조건·정보 신뢰도에 동반 반려동물 적합도를 곱해 반려 편의를 계산한다."""

    policy = candidate.pet_policy
    if policy is None:
        return 0.25
    if policy.policy_type == PetPolicyType.NOT_ALLOWED:
        return 0.0

    openness = {
        PetPolicyType.INDOOR_ALLOWED: 1.0,
        PetPolicyType.PARTIAL_ALLOWED: 0.8,
        PetPolicyType.OUTDOOR_ONLY: 0.6,
        PetPolicyType.UNKNOWN: 0.5,
    }[policy.policy_type]
    required_conditions = sum(
        condition is True
        for condition in (
            policy.carrier_required,
            policy.leash_required,
            policy.vaccination_required,
        )
    )
    convenience = max(0.4, 1 - required_conditions * 0.15)
    reliability = 0.5 + 0.5 * ((policy.reliability_score or 0) / 100)
    score = openness * convenience * reliability
    if policy.policy_type == PetPolicyType.UNKNOWN:
        score *= 0.5
    # 동반 반려동물이 있으면 가장 덜 맞는 반려동물 기준으로 적합도 계수를 곱한다.
    if pets:
        score *= min(_fit_factor(policy, pet) for pet in pets)
    return _clamp(score)


def score_candidates(
    candidates: Sequence[Candidate],
    context: ScoringContext,
) -> list[ScoredCandidate]:
    """하위 점수를 가중 합성하고 총점 내림차순으로 반환한다."""

    if not candidates:
        return []

    max_saved_count = max(candidate.saved_count for candidate in candidates)
    weights = context.weights.model_dump()
    scored: list[ScoredCandidate] = []

    for candidate in candidates:
        sub_scores = {
            "preference": preference_score(
                set(context.preferred_tags), set(candidate.tags), candidate.item_type
            ),
            "pet": pet_score(candidate, context.pets),
            "proximity": max(
                proximity_score(base, (candidate.lat, candidate.lng), context.max_daily_distance_m)
                for base in (context.base_coord, *context.additional_base_coords)
            ),
            "rating": rating_score(candidate.rating_avg),
            "weather": weather_score(candidate.environment, context.precipitation_probability),
            "popularity": _popularity_score(candidate.saved_count, max_saved_count),
        }
        total = sum(weights[name] * score for name, score in sub_scores.items())
        scored.append(
            ScoredCandidate(
                **candidate.model_dump(),
                total_score=_clamp(total),
                sub_scores=sub_scores,
                reason=_reason_from(sub_scores, weights),
            )
        )

    return sorted(scored, key=lambda item: (-item.total_score, item.place_id.int))


def _popularity_score(saved_count: int, max_saved_count: int) -> float:
    if max_saved_count <= 0:
        return 0.0
    return log1p(saved_count) / log1p(max_saved_count)


def _reason_from(sub_scores: dict[str, float], weights: dict[str, float]) -> str:
    active_scores = ((name, score) for name, score in sub_scores.items() if weights[name] > 0)
    strongest = sorted(
        active_scores,
        key=lambda item: (-(item[1] * weights[item[0]]), item[0]),
    )[:2]
    return ", ".join(f"{SCORE_LABELS[name]} {score * 100:.0f}점" for name, score in strongest)


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))
