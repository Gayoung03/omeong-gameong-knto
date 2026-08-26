"""여행 소유권 확인 — 조회·편집 엔드포인트가 공유한다.

같은 확인을 엔드포인트마다 복사해두면 한 곳만 빠뜨렸을 때 남의 여행이 열린다.
그래서 "가져오면서 확인까지" 하는 함수를 한 곳에 모았다. 엔드포인트는
`route = load_owned_route(db, route_id, current_user)` 한 줄만 쓴다.

**없는 것은 404, 남의 것은 403 이다.** 둘을 하나로 합치면(전부 404) 앱은
편해지지만, 반대로 전부 403 으로 합치면 남의 여행 id 를 찍어보며 존재 여부를
알아낼 수 있게 된다. 명세가 둘을 나눠둔 이유다.
"""

import uuid
from collections.abc import Sequence

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import (
    Pet,
    Route,
    RouteChecklistItem,
    RouteDay,
    RouteItem,
    RouteMemo,
    RoutePet,
    RouteRequestPet,
    TravelLog,
    User,
)
from app.db.models.enums import RouteCreationType


def route_detail_options() -> tuple:
    """상세 응답에 필요한 것을 한 번에 담아오는 옵션.

    없으면 일정 개수만큼 DB 를 왕복한다(N+1).
    """
    return (
        selectinload(Route.route_days).selectinload(RouteDay.items).selectinload(RouteItem.place),
        selectinload(Route.pets),
    )


def load_owned_route(
    db: Session, route_id: uuid.UUID, user: User, *, with_detail: bool = False
) -> Route:
    statement = select(Route).where(Route.id == route_id)
    if with_detail:
        statement = statement.options(*route_detail_options())

    route = db.scalar(statement)
    if route is None:
        raise HTTPException(status_code=404, detail="여행을 찾을 수 없습니다")
    if route.user_id != user.id:
        raise HTTPException(status_code=403, detail="다른 사용자의 여행입니다")
    return route


def load_owned_day(db: Session, route_day_id: uuid.UUID, user: User) -> tuple[RouteDay, Route]:
    day = db.scalar(
        select(RouteDay)
        .where(RouteDay.id == route_day_id)
        # 순번을 다시 매기려면 그 날짜의 항목 전체가 필요하다.
        .options(selectinload(RouteDay.items))
    )
    if day is None:
        raise HTTPException(status_code=404, detail="일정 날짜를 찾을 수 없습니다")

    route = load_owned_route(db, day.route_id, user)
    return day, route


def load_owned_item(
    db: Session, route_item_id: uuid.UUID, user: User
) -> tuple[RouteItem, RouteDay, Route]:
    item = db.get(RouteItem, route_item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="일정을 찾을 수 없습니다")

    day, route = load_owned_day(db, item.route_day_id, user)
    return item, day, route


def load_owned_checklist_item(
    db: Session, item_id: uuid.UUID, user: User
) -> tuple[RouteChecklistItem, Route]:
    item = db.get(RouteChecklistItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="체크리스트 항목을 찾을 수 없습니다")

    route = load_owned_route(db, item.route_id, user)
    return item, route


def load_owned_memo(db: Session, memo_id: uuid.UUID, user: User) -> tuple[RouteMemo, Route]:
    memo = db.get(RouteMemo, memo_id)
    if memo is None:
        raise HTTPException(status_code=404, detail="메모를 찾을 수 없습니다")

    route = load_owned_route(db, memo.route_id, user)
    return memo, route


def log_counts_of(db: Session, route_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, int]:
    """여행별 여행기록(travel_logs) 개수. 여행 모아보기 화면 헤더가 쓴다.

    저장된 값이 아니라 조회 시 집계다. 여행을 지워도
    `travel_logs.route_id` 는 ON DELETE SET NULL 이라 기록 자체는 남는다.
    """
    unique_ids = list({route_id for route_id in route_ids})
    if not unique_ids:
        return {}

    rows = db.execute(
        select(TravelLog.route_id, func.count(TravelLog.id))
        .where(TravelLog.route_id.in_(unique_ids))
        .group_by(TravelLog.route_id)
    ).all()
    return {route_id: count for route_id, count in rows}


def pets_of(db: Session, routes: Sequence[Route]) -> dict[uuid.UUID, list[Pet]]:
    """여행별 **여행 자체의** 반려동물.

    출처가 `creation_type` 에 따라 갈린다 — 추천 여행은 요청서에 적어낸
    `route_request_pets`, 수동 여행은 직접 고른 `route_pets` 다
    (docs/api/routes.md). `Route.pets` 관계는 `route_pets` 만 보기 때문에
    추천 여행에서는 비어서 나온다. 그래서 두 경로를 여기서 함께 처리한다.

    기록의 `companions`(`travel_log_pets`)와는 **다른 데이터**다.
    이쪽은 스냅샷이 아니라 현재 프로필을 그대로 읽는다.
    """
    manual_ids = [route.id for route in routes if route.creation_type is RouteCreationType.MANUAL]
    request_ids = {
        route.route_request_id: route.id
        for route in routes
        if route.creation_type is RouteCreationType.RECOMMENDED and route.route_request_id
    }

    result: dict[uuid.UUID, list[Pet]] = {route.id: [] for route in routes}

    if manual_ids:
        rows = db.execute(
            select(RoutePet.route_id, Pet)
            .join(Pet, Pet.id == RoutePet.pet_id)
            .where(RoutePet.route_id.in_(manual_ids))
        ).all()
        for route_id, pet in rows:
            result[route_id].append(pet)

    if request_ids:
        rows = db.execute(
            select(RouteRequestPet.route_request_id, Pet)
            .join(Pet, Pet.id == RouteRequestPet.pet_id)
            .where(RouteRequestPet.route_request_id.in_(request_ids))
        ).all()
        for request_id, pet in rows:
            result[request_ids[request_id]].append(pet)

    return result
