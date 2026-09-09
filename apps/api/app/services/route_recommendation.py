"""추천 요청을 DB 장소 기반 일정으로 생성한다 (생성·편집 orchestrator).

규칙 결과 요약·저장·입력 로딩·앵커·날씨 스냅샷·TourAPI 대조·자연어 편집 제안은
같은 이름의 형제 모듈(`route_recommendation_*`)로 분리했다. 이 모듈은 그것들을
조립하는 흐름(generate_route·편집 시각 재계산·일정 저장)과, 테스트가 모듈 전역으로
교체(monkeypatch)하는 외부 호출(get_route·build·generate_trip_explanation 등)을 갖는다.
공개 이름은 이 모듈에서 그대로 import 하거나 re-export 한다.
"""

import logging
import uuid
from collections.abc import Callable
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import (
    Place,
    PlaceBusinessHour,
    Route,
    RouteDay,
    RouteItem,
    RouteMove,
    RouteRequest,
    RouteRequestStay,
)
from app.db.models.enums import (
    RouteItemSlotStatus,
    RouteStatus,
    ScheduleItemType,
    TransportType,
)
from app.integrations.llm.request_intent import extract_request_intent, merge_preferred_tags
from app.integrations.llm.route_explanation import generate_trip_explanation
from app.integrations.tour_api.kto import TourAPIError, TourPlace, get_nearby_places
from app.integrations.weather.kma import DayForecast, WeatherForecastError, get_daily_forecasts
from app.recommend.common.geo import Coordinate
from app.recommend.config.pace import PACE, effective_rule
from app.recommend.config.tags import normalize_preferred_tags
from app.recommend.filters import filter_candidates
from app.recommend.itinerary import BuildRequest, Itinerary, build
from app.recommend.schemas import Weights
from app.recommend.scoring import ScoringContext, score_candidates
from app.recommend.tmap import TMapError, get_route
from app.recommend.weights import resolve_weights
from app.services.notifications import add_notification, send_pushes
from app.services.route_recommendation_anchors import _day_anchors, _paired_stay_anchor
from app.services.route_recommendation_errors import (
    LocationResolutionError as LocationResolutionError,
)
from app.services.route_recommendation_errors import RecommendationGenerationError
from app.services.route_recommendation_explanation import _explanation_summary
from app.services.route_recommendation_inputs import _linked_pets as _linked_pets
from app.services.route_recommendation_inputs import _pet_profiles_from, _request_inputs
from app.services.route_recommendation_inputs import resolve_location as resolve_location
from app.services.route_recommendation_persistence import (
    _save_alternatives,
    _save_anchor,
    _save_unfilled_candidates,
    _slot_status_of,
)
from app.services.route_recommendation_replacements import clear_day_candidates
from app.services.route_recommendation_replacements import (
    suggest_replacements as suggest_replacements,
)
from app.services.route_recommendation_tour import _match_tour_places, _with_tour_api_note
from app.services.route_recommendation_weather import _upsert_weather_snapshot, _weather_region

logger = logging.getLogger(__name__)


def generate_route(db: Session, route_id: uuid.UUID) -> None:
    """저장된 추천 요청을 필터·점수화·조립하고 결과 행을 만든다."""

    route = db.get(Route, route_id)
    if route is None or route.route_request_id is None:
        raise RecommendationGenerationError("추천 요청을 찾지 못했습니다")
    request = db.get(RouteRequest, route.route_request_id)
    if request is None:
        raise RecommendationGenerationError("추천 요청을 찾지 못했습니다")

    linked_pets, stay_coords, start_coord = _request_inputs(db, request)
    pets = [pet for pet, _ in linked_pets]
    pet_profiles = _pet_profiles_from(linked_pets)
    day_forecasts = _day_forecasts(request, start_coord)
    # 날씨 점수 축은 0(하루 구성 규칙으로 이동)이라 점수엔 영향이 없지만, 스키마 호환을
    # 위해 최대 강수확률을 넘겨둔다.
    precipitation_probability = max(
        (forecast.pop_max for forecast in day_forecasts.values()), default=None
    )

    # request_text 자유문에서 표준 태그를 보충한다(routes.md·설계 8.3-3). **로컬 변수로만**
    # 쓴다 — request ORM 속성을 바꾸면 아래 커밋에 딸려 영속화된다(이번 생성 한정 원칙).
    # 실패는 TourAPI 와 같은 급으로 무시한다 — 추출이 안 돼도 생성은 계속 간다.
    # 과거 요청 행의 preferred_tags 는 한글 라벨일 수 있어(엔진 코드 통일 전 저장분)
    # 읽는 쪽에서 코드로 한 번 더 정규화한다. 새 행은 이미 코드라 그대로 통과한다.
    stored_tags = normalize_preferred_tags(request.preferred_tags or [])
    merged_tags = frozenset(stored_tags)
    if request.request_text:
        try:
            intent = extract_request_intent(request.request_text)
        except Exception as error:
            logger.warning("request_text 추출 예외: %s", type(error).__name__)
            intent = None
        if intent:
            merged_tags = merge_preferred_tags(stored_tags, intent.preferred_tags)

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
            preferred_tags=merged_tags,
            precipitation_probability=precipitation_probability,
            pets=pet_profiles,
        ),
    )
    if not scored:
        raise RecommendationGenerationError("추천할 장소를 찾지 못했습니다")
    scored = [
        _with_tour_api_note(item) if item.place_id in tour_matched_ids else item for item in scored
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
            restaurant_preferred="category:restaurant" in merged_tags,
            day_start_anchors=day_start_anchors,
            day_end_anchors=day_end_anchors,
            pace_rule=effective_rule(request.pace, pet_profiles),
            day_forecasts=day_forecasts,
            # healing 프리셋·weather 기준 신호. 예보와 무관하게 실내 우선 규칙을 켠다.
            indoor_bias=weights.weather > 0,
        ),
        lambda origin, destination, transport, depart_at: get_route(
            db, origin, destination, transport, depart_at
        ),
    )
    # 부분 성공(route-redesign): 식당·저녁이 부족해도 실패하지 않고 빈 슬롯으로 남긴다.
    # 채울 수 있는 장소가 하나도 없을 때(모든 날이 비었음)만 실패로 처리한다.
    if not any(day.items for day in itinerary.days):
        raise RecommendationGenerationError("일정에 배치할 수 있는 장소가 없습니다")

    selected = [item.candidate for day in itinerary.days for item in day.items]
    tour_api_explanation = (
        f"한국관광공사 TourAPI 실시간 관광정보 {len(tour_places)}건을 조회해 "
        f"DB 장소 {len(tour_matched_ids)}건과 대조했습니다."
        if tour_api_succeeded
        else "한국관광공사 TourAPI 실시간 조회에 실패해 DB 장소로 추천했습니다."
    )
    template_explanation = (
        "사용자가 선택한 취향과 우선순위, 숙소 기준 이동 거리를 반영했습니다. "
        + tour_api_explanation
    )
    # 여행 전체 설명은 규칙 결과 요약으로 LLM 1회 생성하고, 실패·미설정 시 템플릿을 쓴다.
    # 최대 10초 블로킹이라 일정 저장(쓰기·행 잠금) '전에' 부른다 — 커넥션·트랜잭션을
    # 오래 점유해 풀이 고갈되는 것을 막는다(request_text 추출과 같은 시점 정책).
    explanation = (
        generate_trip_explanation(
            _explanation_summary(request, itinerary, selected, pet_profiles, weights)
        )
        or template_explanation
    )

    _save_itinerary(db, route, itinerary, day_forecasts, start_coord)
    route.total_score = Decimal(
        str(round(sum(item.total_score for item in selected) / len(selected) * 100, 2))
    )
    route.pet_safety_score = Decimal(
        str(round(sum(item.sub_scores["pet"] for item in selected) / len(selected) * 100, 2))
    )
    route.explanation = explanation
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
            return

        route = db.get(Route, route_id)
        if route is not None:
            notification = add_notification(
                db,
                user_id=route.user_id,
                type="route_ready",
                target_id=route.id,
                title="추천 루트가 완성됐어요",
                content=f"{route.title} 일정을 확인해보세요.",
            )
            db.commit()
            send_pushes(db, notification)


def rebuild_moves(
    db: Session, ordered_items: list[RouteItem], default_transport: TransportType
) -> None:
    """편집 후 route_moves 를 다시 잇는다. **빈 슬롯(unfilled)은 잇지 않는다.**

    기존 이동수단은 물려주고, 물려받을 게 없으면 여행 기본값을 쓴다. 추가·삭제·순서
    변경(엔드포인트)과 빈 슬롯 채우기(서비스)가 같은 로직을 쓰도록 공용화한다.
    """
    connectable = [
        route_item
        for route_item in ordered_items
        if route_item.slot_status != RouteItemSlotStatus.UNFILLED
    ]
    ids = [route_item.id for route_item in ordered_items]
    if not ids:
        return
    previous = {
        move.from_item_id: move.transport
        for move in db.scalars(select(RouteMove).where(RouteMove.from_item_id.in_(ids)))
    }
    db.execute(delete(RouteMove).where(RouteMove.from_item_id.in_(ids)))
    db.flush()
    for current, following in zip(connectable, connectable[1:], strict=False):
        db.add(
            RouteMove(
                from_item_id=current.id,
                to_item_id=following.id,
                transport=previous.get(current.id, default_transport),
            )
        )
    db.flush()


def _resync_anchor_time(route: Route, day: RouteDay, ordered: list[RouteItem]) -> datetime:
    """그날 시각 재계산의 기준 시각. 첫 채워진 항목의 시각, 없으면 그날 시작 기준."""
    first_filled = next(
        (item for item in ordered if item.slot_status != RouteItemSlotStatus.UNFILLED), None
    )
    if first_filled is not None and first_filled.starts_at is not None:
        return first_filled.starts_at
    window_start = time.fromisoformat(PACE[route.pace.value]["window"][0])
    return max(
        route.start_at,
        datetime.combine(day.route_date, window_start, route.start_at.tzinfo),
    )


def replace_route_item(
    db: Session,
    route: Route,
    day: RouteDay,
    item: RouteItem,
    place_id: uuid.UUID,
) -> RouteItem:
    """선택한 DB 장소를 다시 검증한 뒤 일정 항목과 인접 경로를 갱신한다."""

    replacing_stay = item.item_type == ScheduleItemType.ACCOMMODATION
    was_unfilled = item.slot_status == RouteItemSlotStatus.UNFILLED
    if item.recommendation_score is None and item.item_type == ScheduleItemType.CUSTOM:
        raise RecommendationGenerationError("출발지는 장소 교체 대상이 아닙니다")
    if route.route_request_id is None:
        raise RecommendationGenerationError("추천으로 만든 여행의 장소만 교체할 수 있습니다")
    request = db.get(RouteRequest, route.route_request_id)
    if request is None:
        raise RecommendationGenerationError("추천 요청을 찾지 못했습니다")

    linked_pets, stay_coords, start_coord = _request_inputs(db, request)
    pets = [pet for pet, _ in linked_pets]
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
            preferred_tags=frozenset(normalize_preferred_tags(request.preferred_tags or [])),
            # 날씨 축은 하루 구성 규칙으로 옮겨 점수 가중치가 0 이라 편집 경로에선 조회 생략.
            precipitation_probability=None,
            pets=_pet_profiles_from(linked_pets),
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
        changed_item.slot_status = (
            RouteItemSlotStatus.FILLED
            if replacing_stay
            else _slot_status_of(replacement.tier)
        )
        # 숙소 앵커는 stay_minutes 0 을 유지(집계·시각에서 앵커로 취급). 그 외에는 후보의
        # 평균 체류시간으로 채운다 — 빈 슬롯(None)뿐 아니라 일반 교체의 기존 결함도 고친다.
        if not replacing_stay:
            changed_item.stay_minutes = replacement.average_stay_minutes
        changed_item.recommendation_score = (
            None if replacing_stay else Decimal(str(round(replacement.total_score * 100, 2)))
        )
        changed_item.recommendation_reason = (
            "사용자가 선택한 숙소입니다." if replacing_stay else replacement.reason
        )
    db.flush()

    for changed_day, _changed_item in changed_items:
        ordered = sorted(changed_day.items, key=lambda route_item: route_item.sort_order)
        # 빈 슬롯을 채웠으면 그 항목엔 인접 이동이 없었으므로 그 날짜의 이동을 다시 잇는다.
        if was_unfilled:
            rebuild_moves(db, ordered, route.transport)
        resync_item_times(db, route, ordered, _resync_anchor_time(route, changed_day, ordered))
        clear_day_candidates(db, changed_day.id)

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


def resync_item_times(
    db: Session,
    route: Route,
    ordered_items: list[RouteItem],
    anchor_starts_at: datetime | None,
) -> None:
    """순서·장소가 바뀐 뒤 하루 전체 항목의 시각을 앵커부터 다시 잇는다.

    `ordered_items[0]`을 그날의 시작 앵커(day start)에 고정하고, 그 뒤로는
    `_cascade_item_times`가 "이전 항목 종료 시각 + 휴식시간 + 이동시간"만
    반영한다. 순서 변경·장소 교체·항목 추가/삭제처럼 **그날 첫 항목의 시각
    자체가 그대로인** 편집에서 쓴다.
    """
    if not ordered_items or anchor_starts_at is None:
        return

    # 앞쪽 빈 슬롯은 시각 NULL 로 두고(계약: unfilled 는 시각 없음), 첫 채워진 항목을
    # 앵커 시각에 고정한다. 사용자가 빈 슬롯을 맨 앞으로 옮겨도 시각이 생기지 않게 한다.
    index = 0
    while (
        index < len(ordered_items)
        and ordered_items[index].slot_status == RouteItemSlotStatus.UNFILLED
    ):
        ordered_items[index].starts_at = None
        ordered_items[index].ends_at = None
        index += 1
    if index >= len(ordered_items):
        return

    first = ordered_items[index]
    first.starts_at = anchor_starts_at
    # stay_minutes 가 0 이면(숙소·출발지 앵커) ends_at 을 안 쓴다 — 0 분을 더하면
    # ends_at == starts_at 이 되어 DB CheckConstraint(date_order, "ends_at > starts_at")
    # 를 위반한다. 앵커 저장 관례(_save_anchor)도 이 경우 ends_at 을 아예 안 쓴다.
    first.ends_at = (
        anchor_starts_at + timedelta(minutes=first.stay_minutes) if first.stay_minutes else None
    )
    _cascade_item_times(
        db,
        route,
        first.ends_at or anchor_starts_at,
        _route_item_coord(db, first),
        ordered_items[index + 1 :],
    )


def resync_items_after(
    db: Session,
    route: Route,
    item: RouteItem,
    following_items: list[RouteItem],
) -> None:
    """방금 직접 수정한 `item` 자신의 값은 그대로 두고, 그 뒤 항목들만 다시 잇는다.

    `update_route_item`처럼 사용자가 특정 항목의 `starts_at`/`stay_minutes`를
    직접 바꾼 경우에 쓴다 — `item`의 값을 재계산으로 덮어쓰면 사용자가 보낸
    값(예: 모바일의 `shiftEndsAt`이 계산한 `endsAt`)을 잃어버리게 된다.
    """
    if item.starts_at is None:
        return
    _cascade_item_times(
        db,
        route,
        item.ends_at or item.starts_at,
        _route_item_coord(db, item),
        following_items,
    )


def _cascade_item_times(
    db: Session,
    route: Route,
    current_time: datetime,
    current_coord: Coordinate | None,
    items: list[RouteItem],
) -> None:
    """편집된 순서에 맞춰 예상 시각을 다시 잇는다.

    TMAP 또는 영업시간 검증이 불가능한 지점부터는 시각을 `null`로 비운다.
    장소 편집 자체는 유지하고 화면에서 "시간 미정"으로 보여주기 위해서다.
    """
    if not items:
        return

    rest_min = PACE[route.pace.value]["rest_min"]
    for index, item in enumerate(items):
        # 빈 슬롯은 시각 없이 건너뛰고, 이어지는 항목은 이전 채워진 위치에서 계속 잇는다.
        if item.slot_status == RouteItemSlotStatus.UNFILLED:
            item.starts_at = None
            item.ends_at = None
            continue
        coord = _route_item_coord(db, item)
        if coord is None or current_coord is None:
            _clear_estimated_times(items[index:])
            break

        depart_at = current_time + timedelta(minutes=rest_min)
        try:
            leg = get_route(db, current_coord, coord, route.transport, depart_at)
        except TMapError:
            logger.warning("edited route time estimate unavailable", exc_info=True)
            _clear_estimated_times(items[index:])
            break
        arrival = depart_at + timedelta(minutes=leg.duration_min)
        visit = _fit_edited_item_visit(db, item, arrival, route)
        if visit is None:
            _clear_estimated_times(items[index:])
            break
        item.starts_at, item.ends_at = visit
        current_time = item.ends_at or item.starts_at
        current_coord = coord

    db.flush()


def _clear_estimated_times(items: list[RouteItem]) -> None:
    for item in items:
        item.starts_at = None
        item.ends_at = None


def _fit_edited_item_visit(
    db: Session,
    item: RouteItem,
    arrival: datetime,
    route: Route,
) -> tuple[datetime, datetime | None] | None:
    """실제 영업시간 안에서 편집 후 예상 방문 시각을 맞춘다."""

    starts_at = arrival
    day_window_end = datetime.combine(
        arrival.date(), time.fromisoformat(PACE[route.pace.value]["window"][1]), arrival.tzinfo
    )
    closes_at = min(route.end_at, day_window_end)
    if item.place_id is not None:
        day_of_week = (arrival.weekday() + 1) % 7
        hours = db.scalar(
            select(PlaceBusinessHour).where(
                PlaceBusinessHour.place_id == item.place_id,
                PlaceBusinessHour.day_of_week == day_of_week,
            )
        )
        if hours is not None:
            if hours.is_closed:
                return None
            if hours.opens_at is not None:
                starts_at = max(
                    starts_at,
                    datetime.combine(arrival.date(), hours.opens_at, arrival.tzinfo),
                )
            if hours.closes_at is not None:
                closes_at = min(
                    closes_at,
                    datetime.combine(arrival.date(), hours.closes_at, arrival.tzinfo),
                )
            duration = timedelta(minutes=item.stay_minutes or 0)
            if hours.break_start_at is not None and hours.break_end_at is not None:
                break_start = datetime.combine(
                    arrival.date(), hours.break_start_at, arrival.tzinfo
                )
                break_end = datetime.combine(arrival.date(), hours.break_end_at, arrival.tzinfo)
                if starts_at < break_end and starts_at + duration > break_start:
                    starts_at = break_end

    duration = timedelta(minutes=item.stay_minutes or 0)
    if duration <= timedelta(0):
        return starts_at, None
    ends_at = starts_at + duration
    return (starts_at, ends_at) if ends_at <= closes_at else None


def _route_item_coord(db: Session, item: RouteItem) -> Coordinate | None:
    if item.latitude is not None and item.longitude is not None:
        return float(item.latitude), float(item.longitude)
    if item.place_id is None:
        return None
    place = db.get(Place, item.place_id)
    return (float(place.latitude), float(place.longitude)) if place is not None else None


def _day_forecasts(request: RouteRequest, coord: Coordinate) -> dict[date, DayForecast]:
    """여행 날짜별 예보. 예보 범위(3일) 밖·조회 실패면 그 날짜는 없다(규칙 미적용)."""
    dates = {
        date.fromordinal(request.start_at.date().toordinal() + offset)
        for offset in range((request.end_at.date() - request.start_at.date()).days + 1)
    }
    try:
        return get_daily_forecasts(coord[0], coord[1], dates)
    except WeatherForecastError:
        logger.warning("weather forecast unavailable", exc_info=True)
        return {}


def _save_itinerary(
    db: Session,
    route: Route,
    itinerary: Itinerary,
    day_forecasts: dict[date, DayForecast],
    coord: Coordinate,
) -> None:
    region = _weather_region(coord)
    for day_number, day in enumerate(itinerary.days, start=1):
        forecast = day_forecasts.get(day.route_date)
        weather_snapshot_id = (
            _upsert_weather_snapshot(db, region, coord, day.route_date, forecast)
            if forecast is not None
            else None
        )
        route_day = RouteDay(
            route_id=route.id,
            day_number=day_number,
            route_date=day.route_date,
            weather_snapshot_id=weather_snapshot_id,
        )
        db.add(route_day)
        db.flush()
        # 이동(move)은 채워진 항목·앵커만 잇는다. 빈 슬롯은 체인에서 제외한다.
        chain_ids: list[uuid.UUID] = []
        sort_order = 0
        if day.start_anchor is not None:
            chain_ids.append(
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
                slot_status=_slot_status_of(candidate.tier),
            )
            db.add(item)
            db.flush()
            chain_ids.append(item.id)
            sort_order += 1
            _save_alternatives(db, item.id, day.alternatives.get(candidate.place_id, ()))
        for slot in day.unfilled:
            item = RouteItem(
                route_day_id=route_day.id,
                place_id=None,
                item_type=slot.item_type,
                sort_order=sort_order,
                starts_at=None,
                ends_at=None,
                stay_minutes=None,
                recommendation_score=None,
                recommendation_reason=slot.reason,
                slot_status=RouteItemSlotStatus.UNFILLED,
            )
            db.add(item)
            db.flush()
            sort_order += 1
            _save_unfilled_candidates(db, item.id, slot.candidates)
        if day.end_anchor is not None:
            chain_ids.append(
                _save_anchor(db, route_day.id, day.end_anchor, sort_order, day.end_arrival)
            )
            sort_order += 1
        for (from_item_id, to_item_id), move in zip(
            zip(chain_ids, chain_ids[1:], strict=False), day.moves, strict=True
        ):
            db.add(
                RouteMove(
                    from_item_id=from_item_id,
                    to_item_id=to_item_id,
                    transport=move.transport,
                )
            )
