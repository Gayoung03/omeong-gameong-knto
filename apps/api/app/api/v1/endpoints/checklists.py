"""여행 준비 체크리스트 엔드포인트.

route_items 와 달리 `sort_order` 에 UNIQUE 가 없다(인덱스만 있다).
그래서 순번을 다시 매기는 절차가 필요 없고, 앱이 보낸 값을 그대로 쓴다.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.db.models import RouteChecklistItem
from app.db.session import get_db
from app.schemas.route import (
    ChecklistItemCreate,
    ChecklistItemListResponse,
    ChecklistItemResponse,
    ChecklistItemUpdate,
)
from app.services.route_access import load_owned_checklist_item, load_owned_route

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]


@router.get(
    "/routes/{route_id}/checklist-items",
    response_model=ChecklistItemListResponse,
    summary="체크리스트 목록",
)
def list_checklist_items(
    route_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ChecklistItemListResponse:
    load_owned_route(db, route_id, current_user)

    condition = RouteChecklistItem.route_id == route_id
    total = db.scalar(select(func.count(RouteChecklistItem.id)).where(condition)) or 0

    items = db.scalars(
        select(RouteChecklistItem)
        .where(condition)
        # 화면이 pet·travel·etc 로 묶어 보여주므로 분류 안에서 순번대로 준다.
        .order_by(RouteChecklistItem.category, RouteChecklistItem.sort_order)
        .limit(limit)
        .offset(offset)
    ).all()

    return ChecklistItemListResponse(
        items=[ChecklistItemResponse.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/routes/{route_id}/checklist-items",
    response_model=ChecklistItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="체크리스트 항목 추가",
)
def create_checklist_item(
    route_id: uuid.UUID,
    payload: ChecklistItemCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> ChecklistItemResponse:
    load_owned_route(db, route_id, current_user)

    item = RouteChecklistItem(
        route_id=route_id,
        category=payload.category,
        label=payload.label,
        sort_order=payload.sort_order,
        # 사용자가 만든 항목이라 서버가 false 로 고정한다.
        is_recommended=False,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return ChecklistItemResponse.model_validate(item)


@router.patch(
    "/checklist-items/{item_id}",
    response_model=ChecklistItemResponse,
    summary="체크리스트 항목 수정",
)
def update_checklist_item(
    item_id: uuid.UUID,
    payload: ChecklistItemUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> ChecklistItemResponse:
    item, _route = load_owned_checklist_item(db, item_id, current_user)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    db.commit()
    db.refresh(item)
    return ChecklistItemResponse.model_validate(item)


@router.delete(
    "/checklist-items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="체크리스트 항목 삭제",
)
def delete_checklist_item(
    item_id: uuid.UUID, current_user: CurrentUser, db: DbSession
) -> Response:
    """기본 제공 항목(isRecommended=true)도 지울 수 있다.

    지운 뒤 되돌리는 기능은 없다 — 명세가 그렇게 정해뒀다.
    """
    item, _route = load_owned_checklist_item(db, item_id, current_user)
    db.delete(item)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
