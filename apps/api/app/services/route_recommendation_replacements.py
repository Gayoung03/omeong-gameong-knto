"""자연어 편집 제안(suggest_replacements)과 슬롯 후보 정리(clear_day_candidates).

엔드포인트가 `route_recommendation` 에서 re-export 된 이름으로 부른다. 이 모듈은
상위 orchestrator 를 import 하지 않는다(단방향; 입력 로딩은 inputs 에서).
"""

import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import Place, Route, RouteDay, RouteItem, RouteItemCandidate, RouteRequest
from app.db.models.enums import ScheduleItemType
from app.integrations.llm.route_edit import RouteEditIntent
from app.recommend.config.tags import normalize_preferred_tags
from app.recommend.filters import filter_candidates
from app.recommend.schemas import ScoredCandidate, Weights
from app.recommend.scoring import ScoringContext, score_candidates
from app.recommend.weights import resolve_weights
from app.services.route_recommendation_errors import RecommendationGenerationError
from app.services.route_recommendation_inputs import _pet_profiles_from, _request_inputs


def suggest_replacements(
    db: Session,
    route: Route,
    intent: RouteEditIntent,
    *,
    limit: int = 3,
) -> list[ScoredCandidate]:
    """현재 일정과 겹치지 않는 DB 장소를 기존 추천 규칙으로 다시 점수화한다."""

    if route.route_request_id is None:
        raise RecommendationGenerationError("추천으로 만든 여행만 자연어 교체가 가능합니다")
    request = db.get(RouteRequest, route.route_request_id)
    if request is None:
        raise RecommendationGenerationError("추천 요청을 찾지 못했습니다")

    target = db.scalar(
        select(RouteItem)
        .join(RouteDay, RouteDay.id == RouteItem.route_day_id)
        .where(RouteDay.route_id == route.id, RouteItem.id == intent.target_item_id)
    )
    if target is None:
        raise RecommendationGenerationError("교체할 일정 항목을 찾지 못했습니다")

    current_place_ids = set(
        db.scalars(
            select(RouteItem.place_id)
            .join(RouteDay, RouteDay.id == RouteItem.route_day_id)
            .where(RouteDay.route_id == route.id, RouteItem.place_id.is_not(None))
        ).all()
    )
    linked_pets, stay_coords, start_coord = _request_inputs(db, request)
    pets = [pet for pet, _ in linked_pets]
    if intent.location_anchor == "stay" and stay_coords:
        start_coord = stay_coords[0][1]
    elif target.place_id is not None:
        target_place = db.get(Place, target.place_id)
        if target_place is not None:
            start_coord = float(target_place.latitude), float(target_place.longitude)

    replacing_stay = target.item_type == ScheduleItemType.ACCOMMODATION
    candidates = [
        candidate
        for candidate in filter_candidates(db, request, pets, include_accommodation=replacing_stay)
        if candidate.place_id not in current_place_ids
        and (not replacing_stay or candidate.item_type == ScheduleItemType.ACCOMMODATION)
        and (intent.requested_category is None or candidate.item_type == intent.requested_category)
    ]
    weights = (
        Weights(**request.applied_weights)
        if request.applied_weights is not None
        else resolve_weights(request.priority_preset)
    )
    preferred_tags = frozenset(
        [*normalize_preferred_tags(request.preferred_tags or []), *intent.preferred_tags]
    )
    return score_candidates(
        candidates,
        ScoringContext(
            weights=weights,
            base_coord=start_coord,
            additional_base_coords=tuple(dict.fromkeys(coord for _, coord in stay_coords)),
            preferred_tags=preferred_tags,
            # 날씨 축은 하루 구성 규칙으로 옮겨 점수 가중치가 0 이라 편집 경로에선 조회 생략.
            precipitation_probability=None,
            pets=_pet_profiles_from(linked_pets),
        ),
    )[:limit]


def clear_day_candidates(db: Session, day_id: uuid.UUID) -> None:
    """그 날짜 항목들의 슬롯 대안 후보(route_item_candidates)를 모두 지운다.

    교체·추가·삭제·순서 변경으로 슬롯 구성이 바뀌면 기존 후보는 더 이상 맞지 않는다.
    """
    db.execute(
        delete(RouteItemCandidate).where(
            RouteItemCandidate.route_item_id.in_(
                select(RouteItem.id).where(RouteItem.route_day_id == day_id)
            )
        )
    )
