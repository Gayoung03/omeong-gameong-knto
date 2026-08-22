"""여행(route) 조회·관리 엔드포인트."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import CurrentUser
from app.db.models import Route, RouteDay, RouteItem
from app.db.models.enums import RouteStatus
from app.db.session import get_db
from app.schemas.route import RouteDetail, RouteListItem, RouteListResponse

router = APIRouter()


@router.get("/routes", response_model=RouteListResponse, summary="내 여행 목록")
def list_routes(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
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


@router.get("/routes/{route_id}", response_model=RouteDetail, summary="여행 상세")
def get_route(
    route_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> RouteDetail:
    route = db.scalar(
        select(Route)
        .where(Route.id == route_id)
        # 장바구니에 한 번에 담아온다. 없으면 일정 개수만큼 DB 를 왕복한다(N+1).
        .options(
            selectinload(Route.route_days)
            .selectinload(RouteDay.items)
            .selectinload(RouteItem.place),
            selectinload(Route.pets),
        )
    )

    if route is None:
        raise HTTPException(status_code=404, detail="여행을 찾을 수 없습니다")

    if route.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="다른 사용자의 여행입니다")

    return RouteDetail.model_validate(route)
