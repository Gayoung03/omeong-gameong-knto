"""추천 요청을 DB 장소 기반 일정으로 생성한다."""

import logging
import uuid
from collections.abc import Callable
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    Pet,
    Place,
    Route,
    RouteDay,
    RouteItem,
    RouteMove,
    RouteRequest,
    RouteRequestPet,
    RouteRequestStay,
)
from app.db.models.enums import RouteStatus, TransportType
from app.integrations.llm.route_edit import RouteEditIntent
from app.integrations.maps.kakao import GeocodedAddress, geocode_address
from app.integrations.weather.kma import (
    WeatherForecastError,
    get_precipitation_probabilities,
)
from app.recommend.filters import filter_candidates
from app.recommend.itinerary import BuildRequest, Itinerary, build
from app.recommend.schemas import ScoredCandidate, Weights
from app.recommend.scoring import ScoringContext, score_candidates
from app.recommend.tmap import get_route
from app.recommend.weights import resolve_weights

logger = logging.getLogger(__name__)
Coordinate = tuple[float, float]
Geocoder = Callable[[str], GeocodedAddress]


class LocationResolutionError(RuntimeError):
    """DB 장소와 주소 모두에서 좌표를 얻지 못했다."""


class RecommendationGenerationError(RuntimeError):
    """추천 루트를 생성할 수 없다."""


def resolve_location(
    db: Session,
    place_id: uuid.UUID | None,
    address: str | None,
    *,
    geocoder: Geocoder = geocode_address,
) -> Coordinate:
    """DB 장소 좌표를 우선 사용하고, 없을 때만 주소를 변환한다."""

    if place_id is not None:
        place = db.get(Place, place_id)
        if place is None:
            raise LocationResolutionError("DB에서 장소를 찾지 못했습니다")
        return float(place.latitude), float(place.longitude)

    if address and address.strip():
        try:
            result = geocoder(address)
        except Exception as error:
            raise LocationResolutionError("주소를 좌표로 변환하지 못했습니다") from error
        return result.latitude, result.longitude

    raise LocationResolutionError("장소 ID 또는 주소가 필요합니다")


def generate_route(db: Session, route_id: uuid.UUID) -> None:
    """저장된 추천 요청을 필터·점수화·조립하고 결과 행을 만든다."""

    route = db.get(Route, route_id)
    if route is None or route.route_request_id is None:
        raise RecommendationGenerationError("추천 요청을 찾지 못했습니다")
    request = db.get(RouteRequest, route.route_request_id)
    if request is None:
        raise RecommendationGenerationError("추천 요청을 찾지 못했습니다")

    pets, stay_coords, start_coord = _request_inputs(db, request)
    precipitation_probability = _precipitation_probability(request, start_coord)

    weights = (
        Weights(**request.applied_weights)
        if request.applied_weights is not None
        else resolve_weights()
    )
    candidates = filter_candidates(db, request, pets)
    scored = score_candidates(
        candidates,
        ScoringContext(
            weights=weights,
            base_coord=start_coord,
            additional_base_coords=tuple(dict.fromkeys(coord for _, coord in stay_coords)),
            preferred_tags=frozenset(request.preferred_tags or []),
            precipitation_probability=precipitation_probability,
        ),
    )
    if not scored:
        raise RecommendationGenerationError("추천할 장소를 찾지 못했습니다")

    itinerary = build(
        scored,
        BuildRequest(
            start_at=request.start_at,
            end_at=request.end_at,
            pace=request.pace,
            transport=request.transport,
            start_coord=start_coord,
            day_start_coords=_day_start_coords(stay_coords),
        ),
        lambda origin, destination, transport, depart_at: get_route(
            db, origin, destination, transport, depart_at
        ),
    )
    if not any(day.items for day in itinerary.days):
        raise RecommendationGenerationError("일정에 배치할 수 있는 장소가 없습니다")

    _save_itinerary(db, route, itinerary)
    selected = [item.candidate for day in itinerary.days for item in day.items]
    route.total_score = Decimal(
        str(round(sum(item.total_score for item in selected) / len(selected) * 100, 2))
    )
    route.pet_safety_score = Decimal(
        str(round(sum(item.sub_scores["pet"] for item in selected) / len(selected) * 100, 2))
    )
    route.explanation = "사용자가 선택한 취향과 우선순위, 숙소 기준 이동 거리를 반영했습니다."
    route.status = RouteStatus.GENERATED
    db.commit()


def run_route_generation(route_id: uuid.UUID, open_session: Callable) -> None:
    """BackgroundTasks 진입점. 실패해도 요청과 여행 행은 남긴다."""

    with open_session() as db:
        try:
            generate_route(db, route_id)
        except Exception:
            db.rollback()
            route = db.get(Route, route_id)
            if route is not None:
                route.status = RouteStatus.FAILED
                db.commit()
            logger.exception("route recommendation failed", extra={"route_id": str(route_id)})


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
    pets, stay_coords, start_coord = _request_inputs(db, request)
    if intent.location_anchor == "stay" and stay_coords:
        start_coord = stay_coords[0][1]
    elif target.place_id is not None:
        target_place = db.get(Place, target.place_id)
        if target_place is not None:
            start_coord = float(target_place.latitude), float(target_place.longitude)

    candidates = [
        candidate
        for candidate in filter_candidates(db, request, pets)
        if candidate.place_id not in current_place_ids
        and (intent.requested_category is None or candidate.item_type == intent.requested_category)
    ]
    weights = (
        Weights(**request.applied_weights)
        if request.applied_weights is not None
        else resolve_weights(request.priority_preset)
    )
    preferred_tags = frozenset([*(request.preferred_tags or []), *intent.preferred_tags])
    precipitation_probability = _precipitation_probability(request, start_coord)
    return score_candidates(
        candidates,
        ScoringContext(
            weights=weights,
            base_coord=start_coord,
            additional_base_coords=tuple(dict.fromkeys(coord for _, coord in stay_coords)),
            preferred_tags=preferred_tags,
            precipitation_probability=precipitation_probability,
        ),
    )[:limit]


def replace_route_item(
    db: Session,
    route: Route,
    day: RouteDay,
    item: RouteItem,
    place_id: uuid.UUID,
) -> RouteItem:
    """선택한 DB 장소를 다시 검증한 뒤 일정 항목과 인접 경로를 갱신한다."""

    if route.route_request_id is None:
        raise RecommendationGenerationError("추천으로 만든 여행의 장소만 교체할 수 있습니다")
    request = db.get(RouteRequest, route.route_request_id)
    if request is None:
        raise RecommendationGenerationError("추천 요청을 찾지 못했습니다")

    pets, stay_coords, start_coord = _request_inputs(db, request)
    weights = (
        Weights(**request.applied_weights)
        if request.applied_weights is not None
        else resolve_weights(request.priority_preset)
    )
    scored = score_candidates(
        filter_candidates(db, request, pets),
        ScoringContext(
            weights=weights,
            base_coord=start_coord,
            additional_base_coords=tuple(dict.fromkeys(coord for _, coord in stay_coords)),
            preferred_tags=frozenset(request.preferred_tags or []),
            precipitation_probability=_precipitation_probability(request, start_coord),
        ),
    )
    scored_by_id = {candidate.place_id: candidate for candidate in scored}
    replacement = scored_by_id.get(place_id)
    if replacement is None:
        raise RecommendationGenerationError(
            "선택한 장소가 현재 여행의 반려동물·영업 조건에 맞지 않습니다"
        )

    used_elsewhere = db.scalar(
        select(RouteItem.id)
        .join(RouteDay, RouteDay.id == RouteItem.route_day_id)
        .where(
            RouteDay.route_id == route.id,
            RouteItem.place_id == place_id,
            RouteItem.id != item.id,
        )
        .limit(1)
    )
    if used_elsewhere is not None:
        raise RecommendationGenerationError("이미 일정에 포함된 장소입니다")

    item.place_id = replacement.place_id
    item.custom_place_name = None
    item.item_type = replacement.item_type
    item.recommendation_score = Decimal(str(round(replacement.total_score * 100, 2)))
    item.recommendation_reason = replacement.reason
    db.flush()

    _refresh_adjacent_routes(db, day, item, route.transport)

    route_items = list(
        db.scalars(
            select(RouteItem)
            .join(RouteDay, RouteDay.id == RouteItem.route_day_id)
            .where(RouteDay.route_id == route.id, RouteItem.place_id.is_not(None))
        ).all()
    )
    recommendation_scores = [
        float(route_item.recommendation_score)
        for route_item in route_items
        if route_item.recommendation_score is not None
    ]
    pet_scores = [
        scored_by_id[route_item.place_id].sub_scores["pet"]
        for route_item in route_items
        if route_item.place_id in scored_by_id
    ]
    route.total_score = (
        Decimal(str(round(sum(recommendation_scores) / len(recommendation_scores), 2)))
        if recommendation_scores
        else None
    )
    route.pet_safety_score = (
        Decimal(str(round(sum(pet_scores) / len(pet_scores) * 100, 2)))
        if pet_scores
        else None
    )
    route.explanation = "사용자가 선택한 장소로 일정을 변경하고 추천 조건을 다시 확인했습니다."
    route.version += 1
    db.commit()
    db.refresh(item)
    return item


def _refresh_adjacent_routes(
    db: Session,
    day: RouteDay,
    changed: RouteItem,
    default_transport: TransportType,
) -> None:
    ordered = sorted(day.items, key=lambda route_item: route_item.sort_order)
    position = next(
        index for index, route_item in enumerate(ordered) if route_item.id == changed.id
    )
    pairs = []
    if position > 0:
        pairs.append((ordered[position - 1], changed))
    if position + 1 < len(ordered):
        pairs.append((changed, ordered[position + 1]))

    for origin, destination in pairs:
        if origin.place_id is None or destination.place_id is None:
            continue
        origin_place = db.get(Place, origin.place_id)
        destination_place = db.get(Place, destination.place_id)
        if origin_place is None or destination_place is None:
            continue
        move = db.scalar(
            select(RouteMove).where(
                RouteMove.from_item_id == origin.id,
                RouteMove.to_item_id == destination.id,
            )
        )
        get_route(
            db,
            (float(origin_place.latitude), float(origin_place.longitude)),
            (float(destination_place.latitude), float(destination_place.longitude)),
            move.transport if move is not None else default_transport,
            origin.ends_at,
        )


def _request_inputs(
    db: Session,
    request: RouteRequest,
) -> tuple[list[Pet], list[tuple[RouteRequestStay, Coordinate]], Coordinate]:
    pet_ids = list(
        db.scalars(
            select(RouteRequestPet.pet_id).where(RouteRequestPet.route_request_id == request.id)
        ).all()
    )
    pets = list(db.scalars(select(Pet).where(Pet.id.in_(pet_ids))).all()) if pet_ids else []
    stays = list(
        db.scalars(
            select(RouteRequestStay)
            .where(RouteRequestStay.route_request_id == request.id)
            .order_by(RouteRequestStay.check_in_at.nulls_last(), RouteRequestStay.id)
        ).all()
    )
    stay_coords = [(stay, resolve_location(db, stay.place_id, stay.address)) for stay in stays]
    return pets, stay_coords, _start_coord(db, request, stay_coords)


def _start_coord(
    db: Session,
    request: RouteRequest,
    stay_coords: list[tuple[RouteRequestStay, Coordinate]],
) -> Coordinate:
    if request.departure_place_id is not None or request.departure_location:
        return resolve_location(db, request.departure_place_id, request.departure_location)
    if stay_coords:
        return stay_coords[0][1]
    raise LocationResolutionError("출발 장소 또는 숙소 좌표가 필요합니다")


def _precipitation_probability(
    request: RouteRequest,
    coord: Coordinate,
) -> int | None:
    dates = {
        date.fromordinal(request.start_at.date().toordinal() + offset)
        for offset in range((request.end_at.date() - request.start_at.date()).days + 1)
    }
    try:
        forecasts = get_precipitation_probabilities(coord[0], coord[1], dates)
    except WeatherForecastError:
        logger.warning("weather forecast unavailable", exc_info=True)
        return None
    return max(forecasts.values()) if forecasts else None


def _day_start_coords(
    stays: list[tuple[RouteRequestStay, Coordinate]],
) -> dict[date, Coordinate]:
    result: dict[date, Coordinate] = {}
    for stay, coord in stays:
        if stay.check_in_at is None or stay.check_out_at is None:
            continue
        current = stay.check_in_at.date()
        while current < stay.check_out_at.date():
            current = date.fromordinal(current.toordinal() + 1)
            result[current] = coord
    return result


def _save_itinerary(db: Session, route: Route, itinerary: Itinerary) -> None:
    item_ids: dict[uuid.UUID, uuid.UUID] = {}
    for day_number, day in enumerate(itinerary.days, start=1):
        route_day = RouteDay(
            route_id=route.id,
            day_number=day_number,
            route_date=day.route_date,
        )
        db.add(route_day)
        db.flush()
        for sort_order, scheduled in enumerate(day.items):
            candidate = scheduled.candidate
            item = RouteItem(
                route_day_id=route_day.id,
                place_id=candidate.place_id,
                item_type=candidate.item_type,
                sort_order=sort_order,
                starts_at=scheduled.starts_at,
                ends_at=scheduled.ends_at,
                stay_minutes=candidate.average_stay_minutes,
                recommendation_score=Decimal(str(round(candidate.total_score * 100, 2))),
                recommendation_reason=candidate.reason,
            )
            db.add(item)
            db.flush()
            item_ids[candidate.place_id] = item.id
        for move in day.moves:
            db.add(
                RouteMove(
                    from_item_id=item_ids[move.from_place_id],
                    to_item_id=item_ids[move.to_place_id],
                    transport=move.transport,
                )
            )
