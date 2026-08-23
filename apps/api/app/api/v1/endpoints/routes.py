"""여행(route) 조회·관리 엔드포인트."""

import secrets
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.db.models import Route
from app.db.models.enums import RouteStatus
from app.db.session import get_db
from app.schemas.route import (
    RouteDetail,
    RouteListItem,
    RouteListResponse,
    RouteShareResponse,
    RouteUpdate,
    SharedRouteDetail,
)
from app.services.route_access import load_owned_route, route_detail_options

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]

# 명세(docs/api/routes.md PATCH /routes/{routeId})가 허용하는 상태 전이.
# 역방향과 건너뛰기는 422 다. 표로 두면 "왜 이 전이는 안 되는가"를 코드에서
# 바로 읽을 수 있고, 나중에 상태가 늘어도 조건문이 아니라 표만 고치면 된다.
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

    return RouteListResponse(
        items=[RouteListItem.model_validate(route) for route in routes],
        total=total,
        limit=limit,
        offset=offset,
    )


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

    return SharedRouteDetail.model_validate(route)


@router.get("/routes/{route_id}", response_model=RouteDetail, summary="여행 상세")
def get_route(route_id: uuid.UUID, current_user: CurrentUser, db: DbSession) -> RouteDetail:
    route = load_owned_route(db, route_id, current_user, with_detail=True)
    return RouteDetail.model_validate(route)


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
    return RouteDetail.model_validate(route)


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
