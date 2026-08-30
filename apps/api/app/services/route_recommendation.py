"""추천 요청을 DB 장소 기반 일정으로 생성한다."""

import logging
import uuid
from collections.abc import Callable
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

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
from app.db.models.enums import RouteStatus, ScheduleItemType, TransportType
from app.integrations.llm.route_edit import RouteEditIntent
from app.integrations.maps.kakao import GeocodedAddress, geocode_address
from app.integrations.tour_api.kto import TourAPIError, TourPlace, get_nearby_places
from app.integrations.weather.kma import (
    WeatherForecastError,
    get_precipitation_probabilities,
)
from app.recommend.common.geo import haversine_m
from app.recommend.filters import filter_candidates
from app.recommend.itinerary import BuildRequest, Itinerary, RouteAnchor, build
from app.recommend.schemas import Candidate, ScoredCandidate, Weights
from app.recommend.scoring import ScoringContext, score_candidates
from app.recommend.tmap import get_route
from app.recommend.weights import resolve_weights

logger = logging.getLogger(__name__)
Coordinate = tuple[float, float]
Geocoder = Callable[[str], GeocodedAddress]


class LocationResolutionError(RuntimeError):
    """DB 장소와 주소·장소명 모두에서 좌표를 얻지 못했다."""


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
            raise LocationResolutionError(
                "주소 또는 장소명을 좌표로 변환하지 못했습니다"
            ) from error
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
    tour_places: list[TourPlace] = []
    tour_api_succeeded = False
    try:
        tour_places = _tour_api_places(start_coord, stay_coords)
        tour_api_succeeded = True
    except TourAPIError as error:
        logger.warning("TourAPI lookup failed: %s", error)
    candidate_names = dict(
        db.execute(
            select(Place.id, Place.name).where(
                Place.id.in_([candidate.place_id for candidate in candidates])
            )
        ).all()
    )
    tour_matched_ids = _match_tour_places(candidates, candidate_names, tour_places)
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
    scored = [
        item.model_copy(update={"reason": f"{item.reason} · 한국관광공사 TourAPI 실시간 정보 확인"})
        if item.place_id in tour_matched_ids
        else item
        for item in scored
    ]

    day_start_anchors, day_end_anchors = _day_anchors(db, request, stay_coords)
    itinerary = build(
        scored,
        BuildRequest(
            start_at=request.start_at,
            end_at=request.end_at,
            pace=request.pace,
            transport=request.transport,
            start_coord=start_coord,
            restaurant_preferred="category:restaurant" in (request.preferred_tags or []),
            day_start_anchors=day_start_anchors,
            day_end_anchors=day_end_anchors,
        ),
        lambda origin, destination, transport, depart_at: get_route(
            db, origin, destination, transport, depart_at
        ),
    )
    if not any(day.items for day in itinerary.days):
        raise RecommendationGenerationError("일정에 배치할 수 있는 장소가 없습니다")
    if any(
        day.dinner_required
        and (
            not day.items or day.items[-1].candidate.item_type != ScheduleItemType.RESTAURANT
        )
        for day in itinerary.days
    ):
        raise RecommendationGenerationError(
            "저녁 식사가 필요한 날짜에 배치할 수 있는 반려동물 동반 식당이 부족합니다"
        )
    if request.preferred_tags and "category:restaurant" in request.preferred_tags and any(
        day.restaurant_required
        and not any(
            item.candidate.item_type == ScheduleItemType.RESTAURANT for item in day.items
        )
        for day in itinerary.days
    ):
        raise RecommendationGenerationError(
            "맛집 선호를 반영할 수 있는 반려동물 동반 식당이 부족합니다"
        )

    _save_itinerary(db, route, itinerary)
    selected = [item.candidate for day in itinerary.days for item in day.items]
    route.total_score = Decimal(
        str(round(sum(item.total_score for item in selected) / len(selected) * 100, 2))
    )
    route.pet_safety_score = Decimal(
        str(round(sum(item.sub_scores["pet"] for item in selected) / len(selected) * 100, 2))
    )
    tour_api_explanation = (
        f"한국관광공사 TourAPI 실시간 관광정보 {len(tour_places)}건을 조회해 "
        f"DB 장소 {len(tour_matched_ids)}건과 대조했습니다."
        if tour_api_succeeded
        else "한국관광공사 TourAPI 실시간 조회에 실패해 DB 장소로 추천했습니다."
    )
    route.explanation = (
        "사용자가 선택한 취향과 우선순위, 숙소 기준 이동 거리를 반영했습니다. "
        + tour_api_explanation
    )
    route.status = RouteStatus.GENERATED
    db.commit()


def _tour_api_places(
    start_coord: Coordinate,
    stays: list[tuple[RouteRequestStay, Coordinate]],
) -> list[TourPlace]:
    """출발지와 숙소 주변을 매번 조회하고 메모리에만 합친다."""

    coordinates = dict.fromkeys([start_coord, *(coord for _, coord in stays)])
    by_content_id: dict[str, TourPlace] = {}
    for latitude, longitude in coordinates:
        for place in get_nearby_places(latitude, longitude):
            by_content_id[place.content_id] = place
    return list(by_content_id.values())


def _match_tour_places(
    candidates: list[Candidate],
    candidate_names: dict[uuid.UUID, str],
    tour_places: list[TourPlace],
) -> set[uuid.UUID]:
    """원문을 저장하지 않고 제목과 좌표가 맞는 DB 장소 ID만 돌려준다."""

    by_title: dict[str, list[TourPlace]] = {}
    for place in tour_places:
        by_title.setdefault(_normalized_title(place.title), []).append(place)

    matched: set[uuid.UUID] = set()
    for candidate in candidates:
        title = _normalized_title(candidate_names.get(candidate.place_id, ""))
        same_title = by_title.get(title, []) if title else []
        if any(
            haversine_m((candidate.lat, candidate.lng), (place.latitude, place.longitude)) <= 500
            for place in same_title
        ) or any(
            haversine_m((candidate.lat, candidate.lng), (place.latitude, place.longitude)) <= 30
            for place in tour_places
        ):
            matched.add(candidate.place_id)
    return matched


def _normalized_title(value: str) -> str:
    return "".join(character.lower() for character in value if character.isalnum())


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

    replacing_stay = item.item_type == ScheduleItemType.ACCOMMODATION
    if item.recommendation_score is None and item.item_type == ScheduleItemType.CUSTOM:
        raise RecommendationGenerationError("출발지는 장소 교체 대상이 아닙니다")
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
        filter_candidates(db, request, pets, include_accommodation=replacing_stay),
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
    if replacing_stay and replacement is not None:
        if replacement.item_type != ScheduleItemType.ACCOMMODATION:
            replacement = None
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
    if used_elsewhere is not None and not replacing_stay:
        raise RecommendationGenerationError("이미 일정에 포함된 장소입니다")

    changed_items = [(day, item)]
    if replacing_stay:
        paired = _paired_stay_anchor(db, route, day, item)
        if paired is not None:
            changed_items.append(paired)

    for _changed_day, changed_item in changed_items:
        changed_item.place_id = replacement.place_id
        changed_item.custom_place_name = None
        changed_item.custom_address = None
        changed_item.latitude = Decimal(str(replacement.lat))
        changed_item.longitude = Decimal(str(replacement.lng))
        changed_item.item_type = replacement.item_type
        changed_item.recommendation_score = (
            None if replacing_stay else Decimal(str(round(replacement.total_score * 100, 2)))
        )
        changed_item.recommendation_reason = (
            "사용자가 선택한 숙소입니다." if replacing_stay else replacement.reason
        )
    db.flush()

    for changed_day, changed_item in changed_items:
        _refresh_adjacent_routes(db, changed_day, changed_item, route.transport)

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
        Decimal(str(round(sum(pet_scores) / len(pet_scores) * 100, 2))) if pet_scores else None
    )
    route.explanation = "사용자가 선택한 장소로 일정을 변경하고 추천 조건을 다시 확인했습니다."
    route.version += 1
    db.commit()
    db.refresh(item)
    return item


def _paired_stay_anchor(
    db: Session, route: Route, day: RouteDay, item: RouteItem
) -> tuple[RouteDay, RouteItem] | None:
    """숙박일의 도착 숙소와 다음 날 출발 숙소를 함께 바꾼다."""

    ordered = sorted(day.items, key=lambda route_item: route_item.sort_order)
    if item.id == ordered[-1].id:
        target_number = day.day_number + 1
        take_first = True
    elif item.id == ordered[0].id:
        target_number = day.day_number - 1
        take_first = False
    else:
        return None

    adjacent = db.scalar(
        select(RouteDay)
        .where(RouteDay.route_id == route.id, RouteDay.day_number == target_number)
        .options(selectinload(RouteDay.items))
    )
    if adjacent is None or not adjacent.items:
        return None
    adjacent_items = sorted(adjacent.items, key=lambda route_item: route_item.sort_order)
    candidate = adjacent_items[0] if take_first else adjacent_items[-1]
    return (adjacent, candidate) if candidate.item_type == ScheduleItemType.ACCOMMODATION else None


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
        origin_coord = _route_item_coord(db, origin)
        destination_coord = _route_item_coord(db, destination)
        if origin_coord is None or destination_coord is None:
            continue
        move = db.scalar(
            select(RouteMove).where(
                RouteMove.from_item_id == origin.id,
                RouteMove.to_item_id == destination.id,
            )
        )
        get_route(
            db,
            origin_coord,
            destination_coord,
            move.transport if move is not None else default_transport,
            origin.ends_at,
        )


def _route_item_coord(db: Session, item: RouteItem) -> Coordinate | None:
    if item.latitude is not None and item.longitude is not None:
        return float(item.latitude), float(item.longitude)
    if item.place_id is None:
        return None
    place = db.get(Place, item.place_id)
    return (float(place.latitude), float(place.longitude)) if place is not None else None


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
    stay_coords = [
        (
            stay,
            (
                (float(stay.latitude), float(stay.longitude))
                if stay.latitude is not None and stay.longitude is not None
                else resolve_location(db, stay.place_id, stay.address)
            ),
        )
        for stay in stays
    ]
    for stay, coord in stay_coords:
        stay.latitude = Decimal(str(coord[0]))
        stay.longitude = Decimal(str(coord[1]))
    if (request.departure_latitude is None or request.departure_longitude is None) and (
        request.departure_place_id is not None or request.departure_location
    ):
        departure_coord = resolve_location(
            db, request.departure_place_id, request.departure_location
        )
        request.departure_latitude = Decimal(str(departure_coord[0]))
        request.departure_longitude = Decimal(str(departure_coord[1]))
    return pets, stay_coords, _start_coord(db, request, stay_coords)


def _start_coord(
    db: Session,
    request: RouteRequest,
    stay_coords: list[tuple[RouteRequestStay, Coordinate]],
) -> Coordinate:
    if request.departure_latitude is not None and request.departure_longitude is not None:
        return float(request.departure_latitude), float(request.departure_longitude)
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


def _day_anchors(
    db: Session,
    request: RouteRequest,
    stays: list[tuple[RouteRequestStay, Coordinate]],
) -> tuple[dict[date, RouteAnchor], dict[date, RouteAnchor]]:
    starts: dict[date, RouteAnchor] = {}
    ends: dict[date, RouteAnchor] = {}
    for stay, coord in stays:
        if stay.check_in_at is None or stay.check_out_at is None:
            continue
        anchor = _stay_anchor(db, stay, coord)
        current = stay.check_in_at.date()
        while current < stay.check_out_at.date():
            ends[current] = anchor
            current = date.fromordinal(current.toordinal() + 1)
            starts[current] = anchor

    first_date = request.start_at.date()
    last_date = request.end_at.date()
    if request.departure_place_id is not None or request.departure_location:
        starts[first_date] = _departure_anchor(db, request)
    elif first_date in ends:
        starts[first_date] = ends[first_date]
    elif stays:
        starts[first_date] = _stay_anchor(db, stays[0][0], stays[0][1])
    ends.pop(last_date, None)
    return starts, ends


def _stay_anchor(
    db: Session,
    stay: RouteRequestStay,
    coord: Coordinate,
) -> RouteAnchor:
    place = db.get(Place, stay.place_id) if stay.place_id is not None else None
    return RouteAnchor(
        name=stay.name,
        coord=coord,
        item_type=ScheduleItemType.ACCOMMODATION,
        place_id=stay.place_id,
        address=stay.address or (place.address if place is not None else None),
    )


def _departure_anchor(db: Session, request: RouteRequest) -> RouteAnchor:
    place = db.get(Place, request.departure_place_id) if request.departure_place_id else None
    return RouteAnchor(
        name=place.name if place is not None else request.departure_location or "여행 출발지",
        coord=_start_coord(db, request, []),
        item_type=ScheduleItemType.CUSTOM,
        place_id=request.departure_place_id,
        address=(place.address if place is not None else request.departure_location),
    )


def _save_itinerary(db: Session, route: Route, itinerary: Itinerary) -> None:
    for day_number, day in enumerate(itinerary.days, start=1):
        route_day = RouteDay(
            route_id=route.id,
            day_number=day_number,
            route_date=day.route_date,
        )
        db.add(route_day)
        db.flush()
        item_ids: list[uuid.UUID] = []
        sort_order = 0
        if day.start_anchor is not None:
            item_ids.append(
                _save_anchor(db, route_day.id, day.start_anchor, sort_order, day.day_start)
            )
            sort_order += 1
        for scheduled in day.items:
            candidate = scheduled.candidate
            item = RouteItem(
                route_day_id=route_day.id,
                place_id=candidate.place_id,
                item_type=candidate.item_type,
                sort_order=sort_order,
                latitude=Decimal(str(candidate.lat)),
                longitude=Decimal(str(candidate.lng)),
                starts_at=scheduled.starts_at,
                ends_at=scheduled.ends_at,
                stay_minutes=candidate.average_stay_minutes,
                recommendation_score=Decimal(str(round(candidate.total_score * 100, 2))),
                recommendation_reason=candidate.reason,
            )
            db.add(item)
            db.flush()
            item_ids.append(item.id)
            sort_order += 1
        if day.end_anchor is not None:
            item_ids.append(
                _save_anchor(db, route_day.id, day.end_anchor, sort_order, day.end_arrival)
            )
        for (from_item_id, to_item_id), move in zip(
            zip(item_ids, item_ids[1:], strict=False), day.moves, strict=True
        ):
            db.add(
                RouteMove(
                    from_item_id=from_item_id,
                    to_item_id=to_item_id,
                    transport=move.transport,
                )
            )


def _save_anchor(
    db: Session,
    route_day_id: uuid.UUID,
    anchor: RouteAnchor,
    sort_order: int,
    starts_at,
) -> uuid.UUID:
    item = RouteItem(
        route_day_id=route_day_id,
        place_id=anchor.place_id,
        custom_place_name=None if anchor.place_id else anchor.name,
        custom_address=anchor.address,
        latitude=Decimal(str(anchor.coord[0])),
        longitude=Decimal(str(anchor.coord[1])),
        item_type=anchor.item_type,
        sort_order=sort_order,
        starts_at=starts_at,
        stay_minutes=0,
    )
    db.add(item)
    db.flush()
    return item.id
