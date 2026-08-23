"""여행 메모 엔드포인트.

`routeDayId` 가 null 이면 여행 전체 메모, 값이 있으면 그 일차 메모다.
앱의 `TripMemo.scheduleId` 가 이 `routeDayId` 에 대응한다.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.db.models import RouteDay, RouteMemo
from app.db.session import get_db
from app.schemas.route import MemoCreate, MemoListResponse, MemoResponse, MemoUpdate
from app.services.route_access import load_owned_memo, load_owned_route

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]


@router.get("/routes/{route_id}/memos", response_model=MemoListResponse, summary="메모 목록")
def list_memos(
    route_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> MemoListResponse:
    load_owned_route(db, route_id, current_user)

    condition = RouteMemo.route_id == route_id
    total = db.scalar(select(func.count(RouteMemo.id)).where(condition)) or 0

    memos = db.scalars(
        select(RouteMemo)
        .where(condition)
        # 쓴 순서대로 준다. 메모는 목록이 아니라 기록이라 뒤집으면 읽는 흐름이 끊긴다.
        .order_by(RouteMemo.created_at)
        .limit(limit)
        .offset(offset)
    ).all()

    return MemoListResponse(
        items=[MemoResponse.model_validate(memo) for memo in memos],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/routes/{route_id}/memos",
    response_model=MemoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="메모 작성",
)
def create_memo(
    route_id: uuid.UUID,
    payload: MemoCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> MemoResponse:
    load_owned_route(db, route_id, current_user)

    if payload.route_day_id is not None:
        day = db.get(RouteDay, payload.route_day_id)
        # 남의 여행 날짜에 메모를 붙이지 못하게 막는다. FK 만으로는
        # "존재하는 날짜"까지만 보장되고 "내 여행의 날짜"인지는 모른다.
        if day is None or day.route_id != route_id:
            raise HTTPException(status_code=404, detail="일정 날짜를 찾을 수 없습니다")

    memo = RouteMemo(
        route_id=route_id,
        route_day_id=payload.route_day_id,
        title=payload.title,
        content=payload.content,
    )
    db.add(memo)
    db.commit()
    db.refresh(memo)
    return MemoResponse.model_validate(memo)


@router.patch("/memos/{memo_id}", response_model=MemoResponse, summary="메모 수정")
def update_memo(
    memo_id: uuid.UUID,
    payload: MemoUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> MemoResponse:
    """`routeDayId` 는 바꿀 수 없다. 다른 일차로 옮기려면 지우고 다시 쓴다."""
    memo, _route = load_owned_memo(db, memo_id, current_user)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(memo, field, value)

    db.commit()
    db.refresh(memo)
    return MemoResponse.model_validate(memo)


@router.delete(
    "/memos/{memo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="메모 삭제",
)
def delete_memo(memo_id: uuid.UUID, current_user: CurrentUser, db: DbSession) -> Response:
    memo, _route = load_owned_memo(db, memo_id, current_user)
    db.delete(memo)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
