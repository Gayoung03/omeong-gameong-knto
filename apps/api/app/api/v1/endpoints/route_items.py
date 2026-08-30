"""일정 편집 엔드포인트 — 하루 안의 방문 항목을 더하고 고치고 지운다.

주소가 `/routes` 로 시작하지 않는다. 명세(docs/api/routes.md "일정 편집")가
`/route-days/{routeDayId}/items` 와 `/route-items/{routeItemId}` 를 쓰기
때문이다. 항목 하나를 고칠 때 그 항목이 어느 여행 소속인지 앱이 몰라도 되게
하려는 설계다. 소유권 확인은 서버가 항목 → 날짜 → 여행 순으로 거슬러 올라가서 한다.
"""

import uuid
from datetime import timedelta
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.db.models import RouteDay, RouteItem, RouteMove
from app.db.models.enums import TransportType
from app.db.session import get_db
from app.recommend.tmap import TMapError
from app.schemas.route import (
    RouteItemCreate,
    RouteItemOrderUpdate,
    RouteItemPlaceReplace,
    RouteItemResponse,
    RouteItemUpdate,
)
from app.services.place_access import load_visible_place
from app.services.route_access import load_owned_day, load_owned_item
from app.services.route_recommendation import RecommendationGenerationError, replace_route_item

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]


# ---------------------------------------------------------------------------
# 순번 다시 매기기
# ---------------------------------------------------------------------------


def _renumber(db: Session, ordered_items: list[RouteItem]) -> None:
    """`ordered_items` 순서대로 sort_order 를 0 부터 다시 매긴다.

    **두 번에 나눠 쓴다.** route_items 에는 UNIQUE(route_day_id, sort_order) 가
    걸려 있고 PostgreSQL 은 이 제약을 행마다 즉시 검사한다. 0·1·2 를 1·2·3 으로
    한 번에 올리면 중간에 이미 있는 값과 부딪쳐 실패한다.
    그래서 아무와도 겹칠 수 없는 높은 구간으로 한 번 피했다가 0 부터 내려앉힌다.
    """
    if not ordered_items:
        return

    parking = max(item.sort_order for item in ordered_items) + 1000
    for offset, item in enumerate(ordered_items):
        item.sort_order = parking + offset
    db.flush()

    for order, item in enumerate(ordered_items):
        item.sort_order = order
    db.flush()


def _rebuild_moves(
    db: Session, ordered_items: list[RouteItem], default_transport: TransportType
) -> None:
    """route_moves 를 이 날짜 기준으로 다시 잇는다.

    route_moves 에는 "어디에서 어디로, 무엇을 타고"만 남는다. 거리·시간·polyline 은
    route_calculation_cache 가 최대 24시간만 들고 있어서(docs/api/routes.md)
    여기서 계산하지 않는다.

    이동수단은 **원래 그 항목에서 출발하던 이동수단을 물려준다.** 추천이 구간마다
    다른 수단을 골라둘 수 있는데, 순서만 바꿨다고 전부 여행 기본값으로 되돌리면
    그 정보가 사라진다. 물려받을 것이 없을 때만 여행의 기본 이동수단을 쓴다.
    """
    item_ids = [item.id for item in ordered_items]
    if not item_ids:
        return

    previous = {
        move.from_item_id: move.transport
        for move in db.scalars(select(RouteMove).where(RouteMove.from_item_id.in_(item_ids)))
    }
    db.execute(delete(RouteMove).where(RouteMove.from_item_id.in_(item_ids)))
    db.flush()

    for current, following in zip(ordered_items, ordered_items[1:], strict=False):
        db.add(
            RouteMove(
                from_item_id=current.id,
                to_item_id=following.id,
                transport=previous.get(current.id, default_transport),
            )
        )
    db.flush()


def _sorted_items(day: RouteDay) -> list[RouteItem]:
    return sorted(day.items, key=lambda item: item.sort_order)


# ---------------------------------------------------------------------------
# 엔드포인트
# ---------------------------------------------------------------------------


@router.post(
    "/route-days/{route_day_id}/items",
    response_model=RouteItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="일정 항목 추가",
)
def create_route_item(
    route_day_id: uuid.UUID,
    payload: RouteItemCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> RouteItemResponse:
    day, route = load_owned_day(db, route_day_id, current_user)

    # 남의 개인 장소는 일정에 넣을 수 없다 — 없는 장소와 똑같이 404 다.
    place = (
        load_visible_place(db, payload.place_id, current_user)
        if payload.place_id is not None
        else None
    )

    existing = _sorted_items(day)
    # 명세는 "이미 있는 값이면 뒤 항목을 밀어낸다"이다. 목록의 원하는 자리에
    # 끼워 넣고 전체를 다시 매기면 밀어내기가 저절로 된다.
    position = min(payload.sort_order, len(existing))

    stay_minutes = payload.stay_minutes
    if stay_minutes is None and place is not None:
        stay_minutes = place.average_stay_minutes or 60
    ends_at = payload.ends_at
    if ends_at is None and payload.starts_at is not None and stay_minutes is not None:
        ends_at = payload.starts_at + timedelta(minutes=stay_minutes)

    item = RouteItem(
        route_day_id=day.id,
        place_id=payload.place_id,
        custom_place_name=payload.custom_place_name,
        custom_address=place.address if place is not None else None,
        latitude=Decimal(str(place.latitude)) if place is not None else None,
        longitude=Decimal(str(place.longitude)) if place is not None else None,
        item_type=payload.item_type,
        # 잠깐 쓰는 값. 바로 아래 _renumber 가 0 부터 다시 매긴다.
        sort_order=(existing[-1].sort_order + 1) if existing else 0,
        starts_at=payload.starts_at,
        ends_at=ends_at,
        stay_minutes=stay_minutes,
        note=payload.note,
    )
    db.add(item)
    db.flush()

    ordered = existing[:position] + [item] + existing[position:]
    _renumber(db, ordered)
    _rebuild_moves(db, ordered, route.transport)
    db.commit()
    db.refresh(item)
    return RouteItemResponse.model_validate(item)


@router.patch(
    "/route-items/{route_item_id}",
    response_model=RouteItemResponse,
    summary="일정 항목 수정",
)
def update_route_item(
    route_item_id: uuid.UUID,
    payload: RouteItemUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> RouteItemResponse:
    item, _day, _route = load_owned_item(db, route_item_id, current_user)

    # exclude_unset — 안 보낸 필드는 건드리지 않는다. 이게 없으면 시간만 고쳐
    # 보냈는데 메모가 null 로 지워진다.
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    # 한쪽만 보냈을 때도 기존 값과 맞춰 봐야 한다. DB CheckConstraint 가 막긴
    # 하지만 그건 500 이라 앱이 이유를 모른다.
    if item.starts_at and item.ends_at and item.ends_at <= item.starts_at:
        raise HTTPException(status_code=422, detail="endsAt 은 startsAt 보다 뒤여야 합니다")

    db.commit()
    db.refresh(item)
    return RouteItemResponse.model_validate(item)


@router.put(
    "/route-items/{route_item_id}/place",
    response_model=RouteItemResponse,
    summary="일정 장소 교체 확정",
)
def replace_route_item_place(
    route_item_id: uuid.UUID,
    payload: RouteItemPlaceReplace,
    current_user: CurrentUser,
    db: DbSession,
) -> RouteItemResponse:
    """AI 추천 후보와 직접 고른 DB 장소를 같은 규칙으로 확정한다."""

    item, day, route = load_owned_item(db, route_item_id, current_user)
    try:
        replaced = replace_route_item(db, route, day, item, payload.place_id)
    except RecommendationGenerationError as error:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(error)) from error
    except TMapError as error:
        db.rollback()
        raise HTTPException(
            status_code=502, detail="교체 장소의 이동 경로를 계산하지 못했습니다"
        ) from error
    return RouteItemResponse.model_validate(replaced)


@router.put(
    "/route-days/{route_day_id}/items/order",
    response_model=list[RouteItemResponse],
    summary="일정 순서 변경",
)
def reorder_route_items(
    route_day_id: uuid.UUID,
    payload: RouteItemOrderUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> list[RouteItemResponse]:
    day, route = load_owned_day(db, route_day_id, current_user)

    by_id = {item.id: item for item in day.items}
    # 부분만 보내면 남은 항목의 순번을 서버가 짐작해야 한다. 짐작하지 않고
    # 거절한다 — 드래그 화면은 어차피 전체 목록을 들고 있다.
    if len(payload.item_ids) != len(by_id) or set(payload.item_ids) != set(by_id):
        raise HTTPException(status_code=422, detail="이 날짜의 일정 전체를 순서대로 보내야 합니다")

    ordered = [by_id[item_id] for item_id in payload.item_ids]
    _renumber(db, ordered)
    _rebuild_moves(db, ordered, route.transport)
    db.commit()
    return [RouteItemResponse.model_validate(item) for item in ordered]


@router.delete(
    "/route-items/{route_item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="일정 항목 삭제",
)
def delete_route_item(
    route_item_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> Response:
    item, day, route = load_owned_item(db, route_item_id, current_user)

    remaining = [existing for existing in _sorted_items(day) if existing.id != item.id]
    db.delete(item)
    db.flush()

    # 지운 자리를 비워두면 sortOrder 에 구멍이 남는다. 앱의 순번 배지가
    # index + 1 로 그려지므로 화면과 서버 값이 어긋나게 된다.
    _renumber(db, remaining)
    _rebuild_moves(db, remaining, route.transport)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
