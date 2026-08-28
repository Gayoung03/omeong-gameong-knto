"""여행(route) 조회·관리 엔드포인트."""

import logging
import secrets
import uuid
from datetime import timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.db.models import (
    Pet,
    Place,
    Route,
    RouteDay,
    RouteItem,
    RouteMove,
    RoutePet,
    RouteRequest,
    RouteRequestPet,
    RouteRequestStay,
)
from app.db.models.enums import RouteCreationType, RouteStatus
from app.db.session import BackgroundSessionFactory, get_background_session, get_db
from app.integrations.llm.route_edit import (
    RouteEditError,
    RouteEditTimeoutError,
    RouteItemContext,
    interpret_route_edit,
)
from app.integrations.tour_api.kto import TourAPIError, get_nearby_places
from app.recommend.config.tags import normalize_preferred_tags
from app.recommend.itinerary import SUPPORTED_TRANSPORTS
from app.recommend.tmap import get_cached_route
from app.recommend.weights import resolve_weights
from app.schemas.route import (
    RouteCreate,
    RouteDetail,
    RouteDistanceSummary,
    RouteEditSuggestionRequest,
    RouteEditSuggestionResponse,
    RouteGenerationStatus,
    RouteListItem,
    RouteListResponse,
    RouteMoveResponse,
    RouteReplacementSuggestion,
    RouteRequestAccepted,
    RouteRequestCreate,
    RouteShareResponse,
    RouteUpdate,
    SharedRouteDetail,
    TourAPIPlaceResponse,
)
from app.services.place_query import place_stats
from app.services.route_access import (
    load_owned_route,
    log_counts_of,
    route_detail_options,
)
from app.services.route_recommendation import (
    LocationResolutionError,
    RecommendationGenerationError,
    run_route_generation,
    suggest_replacements,
)

router = APIRouter()
logger = logging.getLogger(__name__)

DbSession = Annotated[Session, Depends(get_db)]
OpenSession = Annotated[BackgroundSessionFactory, Depends(get_background_session)]

# 명세(docs/api/routes.md PATCH /routes/{routeId})가 허용하는 상태 전이.
# 역방향과 건너뛰기는 422 다. 표로 두면 "왜 이 전이는 안 되는가"를 코드에서
# 바로 읽을 수 있고, 나중에 상태가 늘어도 조건문이 아니라 표만 고치면 된다.
#: 여행 날짜는 한국 날짜로 센다. 컨테이너는 UTC 로 도는데 그대로 쓰면
#: 이른 아침·늦은 밤 일정에서 날짜가 하루 밀린다.
KST = timezone(timedelta(hours=9))

#: 만들 수 있는 여행 길이의 상한. 기간만큼 route_days 를 미리 만들기 때문에
#: 실수로 몇 년짜리를 보내면 행이 그만큼 생긴다. 제주 여행에 30일이면 충분하다.
MAX_TRIP_DAYS = 30

ALLOWED_STATUS_TRANSITIONS: dict[RouteStatus, set[RouteStatus]] = {
    RouteStatus.GENERATED: {RouteStatus.SAVED},
    RouteStatus.SAVED: {RouteStatus.ONGOING},
    RouteStatus.ONGOING: {RouteStatus.COMPLETED},
}


@router.post(
    "/route-requests",
    response_model=RouteRequestAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    summary="추천 요청 생성 및 루트 생성 시작",
)
def create_route_request(
    payload: RouteRequestCreate,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    db: DbSession,
    open_session: OpenSession,
) -> RouteRequestAccepted:
    """조건을 스냅샷으로 저장하고 추천 생성을 뒷작업에 맡긴다."""

    try:
        weights = resolve_weights(payload.priority_preset, payload.user_criteria)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if payload.transport not in SUPPORTED_TRANSPORTS:
        raise HTTPException(
            status_code=422,
            detail=f"현재 루트 추천에서 지원하지 않는 이동수단입니다: {payload.transport.value}",
        )

    pets = []
    if payload.pet_ids:
        pets = list(db.scalars(select(Pet).where(Pet.id.in_(payload.pet_ids))).all())
        if len(pets) != len(set(payload.pet_ids)):
            raise HTTPException(status_code=404, detail="반려동물을 찾을 수 없습니다")
        if any(pet.user_id != current_user.id for pet in pets):
            raise HTTPException(status_code=403, detail="다른 사용자의 반려동물입니다")

    place_ids = {
        place_id
        for place_id in [payload.departure_place_id, *(stay.place_id for stay in payload.stays)]
        if place_id is not None
    }
    if place_ids:
        found_ids = set(db.scalars(select(Place.id).where(Place.id.in_(place_ids))).all())
        if found_ids != place_ids:
            raise HTTPException(status_code=404, detail="출발지 또는 숙소 장소를 찾을 수 없습니다")

    preferred_tags = normalize_preferred_tags(payload.preferred_tags)
    request = RouteRequest(
        user_id=current_user.id,
        title=payload.title,
        start_at=payload.start_at,
        end_at=payload.end_at,
        departure_location=payload.departure_location,
        departure_place_id=payload.departure_place_id,
        pace=payload.pace,
        transport=payload.transport,
        companion_count=payload.companion_count,
        preferred_tags=preferred_tags,
        priority_preset=payload.priority_preset,
        applied_weights=weights.model_dump(),
        request_text=payload.request_text,
    )
    db.add(request)
    db.flush()

    for pet in pets:
        db.add(RouteRequestPet(route_request_id=request.id, pet_id=pet.id))
    for stay in payload.stays:
        db.add(
            RouteRequestStay(
                route_request_id=request.id,
                place_id=stay.place_id,
                name=stay.name,
                address=stay.address,
                check_in_at=stay.check_in_at,
                check_out_at=stay.check_out_at,
            )
        )

    route = Route(
        route_request_id=request.id,
        user_id=current_user.id,
        title=payload.title or "추천 제주 여행",
        status=RouteStatus.GENERATING,
        creation_type=RouteCreationType.RECOMMENDED,
        version=1,
        start_at=payload.start_at,
        end_at=payload.end_at,
        pace=payload.pace,
        transport=payload.transport,
        style_keywords=payload.preferred_tags,
    )
    db.add(route)
    db.flush()
    for pet in pets:
        db.add(RoutePet(route_id=route.id, pet_id=pet.id))
    db.commit()

    background_tasks.add_task(run_route_generation, route.id, open_session)
    return RouteRequestAccepted(
        route_id=route.id,
        route_request_id=request.id,
        status=route.status,
        version=route.version,
    )


@router.get("/routes", response_model=RouteListResponse, summary="내 여행 목록")
def list_routes(
    current_user: CurrentUser,
    db: DbSession,
    status: Annotated[list[RouteStatus] | None, Query(description="여러 개 가능")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> RouteListResponse:
    conditions = [Route.user_id == current_user.id]
    if status:
        conditions.append(Route.status.in_(status))

    # 전체 개수는 따로 센다. items 는 limit 으로 잘리지만 total 은 잘리지 않는다.
    total = db.scalar(select(func.count(Route.id)).where(*conditions)) or 0

    routes = db.scalars(
        select(Route).where(*conditions).order_by(Route.start_at.desc()).limit(limit).offset(offset)
    ).all()

    items = [RouteListItem.model_validate(route) for route in routes]
    # 여행마다 따로 세면 목록 하나에 쿼리가 개수만큼 나간다. 한 번에 세서 나눠 담는다.
    counts = log_counts_of(db, [route.id for route in routes])
    for item in items:
        item.log_count = counts.get(item.id, 0)

    return RouteListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/routes",
    response_model=RouteDetail,
    status_code=status.HTTP_201_CREATED,
    summary="여행 직접 만들기",
)
def create_route(payload: RouteCreate, current_user: CurrentUser, db: DbSession) -> RouteDetail:
    """추천을 받지 않고 사용자가 직접 만드는 여행.

    **여행 껍데기만 만들고 일정은 비워둔다.** 일정은 만든 뒤 일정 편집 API 로
    채운다(docs/api/routes.md "수동 생성" 절의 유력안). 작성 도중 앱이 꺼져도
    만든 여행이 남고, 일정 추가·수정 API 를 그대로 재사용한다.

    **대신 날짜(route_days)는 서버가 미리 만들어 준다.** 일정 추가는
    `POST /route-days/{routeDayId}/items` 라 routeDayId 가 있어야 하는데,
    날짜를 만드는 엔드포인트는 명세에 없다. 여행 기간이 정해지면 날짜도
    정해지므로 여기서 함께 만드는 것이 맞다.

    `status` 는 `saved` 로 시작한다 — 추천 흐름의 `generating` 은 만들어지는
    중이라는 뜻이라 수동 여행에 맞지 않는다. `version` 은 재생성이 없어 항상 1 이다.
    """
    start_date = payload.start_at.astimezone(KST).date()
    end_date = payload.end_at.astimezone(KST).date()
    day_count = (end_date - start_date).days + 1
    if day_count > MAX_TRIP_DAYS:
        raise HTTPException(
            status_code=422, detail=f"여행은 최대 {MAX_TRIP_DAYS}일까지 만들 수 있습니다"
        )

    pets = []
    if payload.pet_ids:
        pets = list(db.scalars(select(Pet).where(Pet.id.in_(payload.pet_ids))).all())
        if len(pets) != len(set(payload.pet_ids)):
            raise HTTPException(status_code=404, detail="반려동물을 찾을 수 없습니다")
        for pet in pets:
            if pet.user_id != current_user.id:
                raise HTTPException(status_code=403, detail="다른 사용자의 반려동물입니다")

    route = Route(
        user_id=current_user.id,
        title=payload.title,
        status=RouteStatus.SAVED,
        # route_request_id 는 비워둔다. routes 의 CHECK 제약이
        # "추천이면 요청서 필수, 수동이면 요청서 금지"를 강제한다.
        creation_type=RouteCreationType.MANUAL,
        version=1,
        start_at=payload.start_at,
        end_at=payload.end_at,
        pace=payload.pace,
        transport=payload.transport,
        style_keywords=payload.style_keywords,
        cover_image_url=payload.cover_image_url,
        memo=payload.memo,
    )
    db.add(route)
    db.flush()

    for offset in range(day_count):
        db.add(
            RouteDay(
                route_id=route.id,
                day_number=offset + 1,
                route_date=start_date + timedelta(days=offset),
            )
        )
    for pet in pets:
        db.add(RoutePet(route_id=route.id, pet_id=pet.id))

    db.commit()

    created = load_owned_route(db, route.id, current_user, with_detail=True)
    return _fill_computed(db, created, RouteDetail.model_validate(created))


# 이 엔드포인트는 아래 /routes/{route_id} **보다 먼저** 등록해야 한다.
# FastAPI 는 등록 순서대로 주소를 맞춰보기 때문에, 순서가 뒤바뀌면
# "shared" 를 routeId(UUID) 로 읽으려다 422 가 난다.
@router.get(
    "/routes/shared/{share_token}",
    response_model=SharedRouteDetail,
    summary="공유 링크로 여행 보기",
)
def get_shared_route(share_token: str, db: DbSession) -> SharedRouteDetail:
    """인증이 없다. 토큰을 아는 사람이면 누구나 본다."""
    route = db.scalar(
        select(Route)
        .where(Route.share_token == share_token, Route.is_public.is_(True))
        .options(*route_detail_options())
    )
    # 공유가 꺼진 여행과 없는 토큰을 같은 404 로 돌려준다. 나눠서 알려주면
    # "이 토큰은 존재하지만 지금은 비공개"라는 사실이 새어 나간다.
    if route is None:
        raise HTTPException(status_code=404, detail="공유된 여행을 찾을 수 없습니다")

    return _fill_computed(db, route, SharedRouteDetail.model_validate(route))


@router.get(
    "/routes/{route_id}/status",
    response_model=RouteGenerationStatus,
    summary="추천 루트 생성 상태 확인",
)
def get_route_status(
    route_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> RouteGenerationStatus:
    route = load_owned_route(db, route_id, current_user)
    return RouteGenerationStatus(
        route_id=route.id,
        status=route.status,
        version=route.version,
        failure_reason=(
            "추천 루트를 생성하지 못했습니다" if route.status == RouteStatus.FAILED else None
        ),
    )


@router.post(
    "/routes/{route_id}/edit-suggestions",
    response_model=RouteEditSuggestionResponse,
    summary="자연어 루트 부분 수정 후보 추천",
)
def create_route_edit_suggestions(
    route_id: uuid.UUID,
    payload: RouteEditSuggestionRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> RouteEditSuggestionResponse:
    """LLM은 수정 의도만 해석하고 실제 대체 장소는 DB 추천 엔진이 고른다."""

    route = load_owned_route(db, route_id, current_user)
    rows = db.execute(
        select(RouteItem, Place)
        .join(RouteDay, RouteDay.id == RouteItem.route_day_id)
        .outerjoin(Place, Place.id == RouteItem.place_id)
        .where(RouteDay.route_id == route.id)
        .order_by(RouteDay.day_number, RouteItem.sort_order)
    ).all()
    contexts = [
        RouteItemContext(
            item_id=row.RouteItem.id,
            name=(
                row.Place.name
                if row.Place is not None
                else row.RouteItem.custom_place_name or "일정"
            ),
            category=row.RouteItem.item_type.value,
        )
        for row in rows
    ]
    if payload.target_item_id is not None:
        contexts = [context for context in contexts if context.item_id == payload.target_item_id]
        if not contexts:
            raise HTTPException(status_code=404, detail="교체할 일정 항목을 찾을 수 없습니다")
    try:
        intent = interpret_route_edit(contexts, payload.instruction)
        candidates = suggest_replacements(db, route, intent)
    except RouteEditTimeoutError as error:
        raise HTTPException(status_code=504, detail="루트 수정 해석이 늦어지고 있어요") from error
    except RouteEditError as error:
        raise HTTPException(status_code=502, detail="루트 수정 요청을 이해하지 못했어요") from error
    except (LocationResolutionError, RecommendationGenerationError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    places = {
        place.id: place
        for place in db.scalars(
            select(Place).where(Place.id.in_([candidate.place_id for candidate in candidates]))
        ).all()
    }
    suggestions = [
        RouteReplacementSuggestion(
            place_id=candidate.place_id,
            name=places[candidate.place_id].name,
            category=places[candidate.place_id].category,
            address=places[candidate.place_id].address,
            primary_image_url=places[candidate.place_id].primary_image_url,
            recommendation_score=round(candidate.total_score * 100, 2),
            recommendation_reason=candidate.reason,
        )
        for candidate in candidates
        if candidate.place_id in places
    ]
    return RouteEditSuggestionResponse(
        target_item_id=intent.target_item_id,
        interpretation=intent.interpretation,
        suggestions=suggestions,
    )


@router.get("/routes/{route_id}", response_model=RouteDetail, summary="여행 상세")
def get_route(route_id: uuid.UUID, current_user: CurrentUser, db: DbSession) -> RouteDetail:
    route = load_owned_route(db, route_id, current_user, with_detail=True)
    return _fill_computed(db, route, RouteDetail.model_validate(route))


@router.patch("/routes/{route_id}", response_model=RouteDetail, summary="여행 수정")
def update_route(
    route_id: uuid.UUID,
    payload: RouteUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> RouteDetail:
    route = load_owned_route(db, route_id, current_user, with_detail=True)

    changes = payload.model_dump(exclude_unset=True)

    if "status" in changes and changes["status"] is not None:
        next_status = changes["status"]
        # 같은 상태로 다시 보내는 것은 통과시킨다. 앱이 저장 버튼을 두 번
        # 눌렀다고 실패로 보이면 화면이 이유 없이 붉어진다.
        if next_status != route.status:
            allowed = ALLOWED_STATUS_TRANSITIONS.get(route.status, set())
            if next_status not in allowed:
                raise HTTPException(
                    status_code=422,
                    detail=f"{route.status} 에서 {next_status} 로는 바꿀 수 없습니다",
                )

    for field, value in changes.items():
        setattr(route, field, value)

    db.commit()
    db.refresh(route)
    return _fill_computed(db, route, RouteDetail.model_validate(route))


@router.delete(
    "/routes/{route_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="여행 삭제",
)
def delete_route(route_id: uuid.UUID, current_user: CurrentUser, db: DbSession) -> Response:
    """물리 삭제다. routes 에 deleted_at 이 없다.

    route_days·route_items·route_moves·route_checklist_items·route_memos 는
    ON DELETE CASCADE 로 함께 사라지지만, travel_logs.route_id 는
    ON DELETE SET NULL 이라 **여행 기록과 사진은 남는다.**
    """
    route = load_owned_route(db, route_id, current_user)
    db.delete(route)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/routes/{route_id}/share",
    response_model=RouteShareResponse,
    summary="공유 링크 발급",
)
def share_route(
    route_id: uuid.UUID, current_user: CurrentUser, db: DbSession
) -> RouteShareResponse:
    route = load_owned_route(db, route_id, current_user)

    # 이미 발급됐으면 기존 토큰을 그대로 돌려준다. 누를 때마다 새로 만들면
    # 예전에 보낸 링크가 조용히 죽는다.
    if route.share_token is None:
        route.share_token = _new_share_token(db)

    route.is_public = True
    db.commit()
    db.refresh(route)

    return RouteShareResponse(share_token=route.share_token, is_public=route.is_public)


def _new_share_token(db: Session) -> str:
    """아무도 안 쓰는 공유 토큰을 만든다.

    share_token 에 UNIQUE 가 걸려 있어 부딪치면 INSERT 가 실패한다. 확률은
    낮지만 그때 500 을 내는 대신 몇 번 다시 뽑는다.
    """
    for _ in range(5):
        token = secrets.token_hex(5)  # 10글자
        if db.scalar(select(Route.id).where(Route.share_token == token)) is None:
            return token

    raise HTTPException(status_code=500, detail="공유 링크를 만들지 못했습니다")


def _fill_computed(
    db: Session, route: Route, detail: RouteDetail | SharedRouteDetail
) -> RouteDetail | SharedRouteDetail:
    """DB 컬럼이 아닌 값들을 채운다.

    `model_validate(route)` 는 ORM 객체에 있는 것만 옮겨온다. 이 값들은 세어야
    나오는 것이라 만들어진 응답에 나중에 넣는다.

    **아직 못 채우는 것** — weather(기상청), stays(추천 요청서).
    데이터 소스가 생기면 여기에 같이 붙인다.
    """
    detail.log_count = log_counts_of(db, [route.id]).get(route.id, 0)

    places = [
        item.place for day in detail.route_days for item in day.items if item.place is not None
    ]
    stats = place_stats(db, [place.id for place in places])
    for place in places:
        stat = stats.get(place.id)
        if stat is None:
            continue
        place.rating = stat.rating
        place.review_count = stat.review_count
        place.pet_policy_type = stat.pet_policy_type

    orm_items = {item.id: item for day in route.route_days for item in day.items}
    response_items = {item.id: item for day in detail.route_days for item in day.items}
    item_ids = list(orm_items)
    moves = (
        list(db.scalars(select(RouteMove).where(RouteMove.from_item_id.in_(item_ids))).all())
        if item_ids
        else []
    )
    total_distance_meters = 0
    total_duration_minutes = 0
    for move in moves:
        source = orm_items.get(move.from_item_id)
        destination = orm_items.get(move.to_item_id)
        if source is None or destination is None:
            continue
        source_coord = _item_coord(source)
        destination_coord = _item_coord(destination)
        if source_coord is None or destination_coord is None:
            continue
        leg = get_cached_route(
            db,
            source_coord,
            destination_coord,
            move.transport,
        )
        if leg is None:
            continue
        response_items[move.from_item_id].move_to_next = RouteMoveResponse(
            transport=move.transport,
            distance_meters=leg.distance_m,
            duration_minutes=leg.duration_min,
        )
        total_distance_meters += leg.distance_m
        total_duration_minutes += leg.duration_min

    detail.distance_summary = RouteDistanceSummary(
        total_distance_meters=total_distance_meters,
        total_duration_minutes=total_duration_minutes,
    )
    center = next(
        (
            coord
            for day in route.route_days
            for item in sorted(day.items, key=lambda route_item: route_item.sort_order)
            if (coord := _item_coord(item)) is not None
        ),
        None,
    )
    if center is not None:
        try:
            detail.tour_api_places = [
                TourAPIPlaceResponse(
                    content_id=place.content_id,
                    title=place.title,
                    address=place.address,
                    latitude=place.latitude,
                    longitude=place.longitude,
                    image_url=place.image_url,
                )
                for place in get_nearby_places(*center, limit=3)
            ]
        except TourAPIError as error:
            logger.warning("TourAPI route highlights lookup failed: %s", error)

    return detail


def _item_coord(item: RouteItem) -> tuple[float, float] | None:
    if item.latitude is not None and item.longitude is not None:
        return float(item.latitude), float(item.longitude)
    if item.place is not None:
        return float(item.place.latitude), float(item.place.longitude)
    return None
