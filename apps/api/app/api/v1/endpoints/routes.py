"""여행(route) 조회·관리 엔드포인트."""

import secrets
import uuid
from datetime import timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.db.models import Pet, Route, RouteDay, RoutePet
from app.db.models.enums import RouteCreationType, RouteStatus
from app.db.session import get_db
from app.schemas.route import (
    RouteCreate,
    RouteDetail,
    RouteListItem,
    RouteListResponse,
    RouteShareResponse,
    RouteUpdate,
    SharedRouteDetail,
)
from app.services.place_query import place_stats
from app.services.route_access import (
    load_owned_route,
    log_counts_of,
    route_detail_options,
)

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]

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
    """DB 컬럼이 아닌 값들을 채운다 — 여행기록 개수, 그리고 장소의 평점·리뷰수·동반정책.

    `model_validate(route)` 는 ORM 객체에 있는 것만 옮겨온다. 이 값들은 세어야
    나오는 것이라 만들어진 응답에 나중에 넣는다.

    **아직 못 채우는 것** — weather(기상청), moveToNext·distanceSummary(TMAP),
    stays(추천 요청서). 데이터 소스가 생기면 여기에 같이 붙인다.
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

    return detail
