"""일자별 출발지·숙소 앵커 계산.

`route_recommendation.generate_route`(하루 앵커)와 편집 경로(숙박 앵커 짝)가 쓴다.
이 모듈은 상위 orchestrator 를 import 하지 않는다(단방향; 좌표 해석은 inputs 에서).
"""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Place, Route, RouteDay, RouteItem, RouteRequest, RouteRequestStay
from app.db.models.enums import ScheduleItemType
from app.recommend.common.geo import Coordinate
from app.recommend.itinerary import RouteAnchor
from app.services.route_recommendation_inputs import _start_coord


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
