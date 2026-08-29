import uuid
from datetime import datetime, time
from zoneinfo import ZoneInfo

from app.db.models.enums import ScheduleItemType, TransportType, TripPace
from app.recommend.itinerary import DINNER_START, BuildRequest, RouteAnchor, build
from app.recommend.schemas import BusinessHour, ScoredCandidate
from app.recommend.tmap import RouteLeg

KST = ZoneInfo("Asia/Seoul")


def _candidate(
    score: float,
    *,
    item_type: ScheduleItemType = ScheduleItemType.ATTRACTION,
    lat: float = 33.4996,
    lng: float = 126.5312,
    stay_minutes: int = 60,
    business_hours: list[BusinessHour] | None = None,
) -> ScoredCandidate:
    return ScoredCandidate(
        place_id=uuid.uuid4(),
        lat=lat,
        lng=lng,
        item_type=item_type,
        environment="outdoor",
        average_stay_minutes=stay_minutes,
        business_hours=business_hours or [],
        total_score=score,
        sub_scores={
            "preference": score,
            "pet": score,
            "proximity": score,
            "rating": 0,
            "weather": score,
            "popularity": 0,
        },
        reason="사용자 취향에 맞는 장소",
    )


def _request(pace: TripPace = TripPace.NORMAL) -> BuildRequest:
    return BuildRequest(
        start_at=datetime(2026, 8, 31, 9, tzinfo=KST),
        end_at=datetime(2026, 8, 31, 19, tzinfo=KST),
        pace=pace,
        transport=TransportType.RENTAL_CAR,
        start_coord=(33.5, 126.53),
    )


def test_relaxed_pace_selects_at_most_three_and_calls_only_selected_routes() -> None:
    candidates = [
        _candidate(score, lat=33.5 + index / 1000) for index, score in enumerate((0.9, 0.8, 0.7))
    ]
    candidates.append(_candidate(0.6, item_type=ScheduleItemType.RESTAURANT, lat=33.504))
    calls: list[tuple] = []

    def fake_route(*args):
        calls.append(args)
        return RouteLeg(distance_m=1000, duration_min=10, polyline=None)

    result = build(candidates, _request(TripPace.RELAXED), fake_route)

    assert len(result.days[0].items) == 3
    assert len(calls) == 3
    assert len(result.days[0].moves) == 2
    assert result.days[0].items[0].starts_at == datetime(2026, 8, 31, 10, 10, tzinfo=KST)
    assert result.days[0].items[1].starts_at == datetime(2026, 8, 31, 13, 10, tzinfo=KST)
    assert result.days[0].items[-1].ends_at >= datetime(2026, 8, 31, 17, tzinfo=KST)
    assert result.days[0].items[-1].candidate.item_type == ScheduleItemType.RESTAURANT
    assert result.days[0].items[-1].starts_at >= datetime(2026, 8, 31, 17, tzinfo=KST)


def test_a_day_contains_at_most_one_cafe() -> None:
    cafes = [
        _candidate(score, item_type=ScheduleItemType.CAFE, lat=33.5 + index / 1000)
        for index, score in enumerate((0.99, 0.98, 0.97))
    ]
    attraction = _candidate(0.5, item_type=ScheduleItemType.ATTRACTION, lat=33.51)
    dinner = _candidate(0.4, item_type=ScheduleItemType.RESTAURANT, lat=33.52)

    result = build(
        [*cafes, attraction, dinner],
        _request(TripPace.NORMAL),
        lambda *_args: RouteLeg(distance_m=1000, duration_min=10, polyline=None),
    )

    assert (
        sum(item.candidate.item_type == ScheduleItemType.CAFE for item in result.days[0].items) == 1
    )
    assert any(
        item.candidate.item_type == ScheduleItemType.ATTRACTION for item in result.days[0].items
    )


def test_each_day_ends_with_dinner_after_five() -> None:
    request = BuildRequest(
        start_at=datetime(2026, 8, 31, 9, tzinfo=KST),
        end_at=datetime(2026, 9, 1, 18, tzinfo=KST),
        pace=TripPace.NORMAL,
        transport=TransportType.RENTAL_CAR,
        start_coord=(33.5, 126.53),
    )
    candidates = [
        *[_candidate(0.8 - index / 100, lat=33.5 + index / 1000) for index in range(6)],
        _candidate(0.7, item_type=ScheduleItemType.RESTAURANT, lat=33.51),
        _candidate(0.69, item_type=ScheduleItemType.RESTAURANT, lat=33.52),
    ]

    result = build(
        candidates,
        request,
        lambda *_args: RouteLeg(distance_m=1000, duration_min=10, polyline=None),
    )

    assert len(result.days) == 2
    assert all(day.dinner_required for day in result.days)
    assert all(
        day.items[-1].candidate.item_type == ScheduleItemType.RESTAURANT
        and day.items[-1].starts_at.time() >= DINNER_START
        for day in result.days
    )


def test_last_day_before_five_does_not_require_dinner() -> None:
    request = BuildRequest(
        start_at=datetime(2026, 8, 31, 9, tzinfo=KST),
        end_at=datetime(2026, 9, 1, 15, tzinfo=KST),
        pace=TripPace.NORMAL,
        transport=TransportType.RENTAL_CAR,
        start_coord=(33.5, 126.53),
    )
    candidates = [
        *[_candidate(0.8 - index / 100, lat=33.5 + index / 1000) for index in range(6)],
        _candidate(0.7, item_type=ScheduleItemType.RESTAURANT, lat=33.51),
    ]

    result = build(
        candidates,
        request,
        lambda *_args: RouteLeg(distance_m=1000, duration_min=10, polyline=None),
    )

    assert len(result.days) == 2
    assert result.days[0].dinner_required is True
    assert result.days[0].items[-1].candidate.item_type == ScheduleItemType.RESTAURANT
    assert result.days[1].dinner_required is False
    assert result.days[1].items
    assert result.days[1].items[-1].candidate.item_type != ScheduleItemType.RESTAURANT


def test_candidate_closed_before_actual_arrival_is_skipped() -> None:
    monday = BusinessHour(day_of_week=1, opens_at=time(9), closes_at=time(14))
    candidate = _candidate(0.9, business_hours=[monday])

    def slow_route(*_args):
        return RouteLeg(distance_m=100_000, duration_min=360, polyline=None)

    result = build([candidate], _request(), slow_route)

    assert result.days[0].items == ()


def test_visit_overlapping_break_starts_after_break() -> None:
    monday = BusinessHour(
        day_of_week=1,
        opens_at=time(9),
        closes_at=time(18),
        break_start_at=time(12),
        break_end_at=time(13),
    )
    candidate = _candidate(0.9, business_hours=[monday])

    def route_during_lunch(*_args):
        return RouteLeg(distance_m=1000, duration_min=180, polyline=None)

    result = build([candidate], _request(), route_during_lunch)

    item = result.days[0].items[0]
    assert item.starts_at == datetime(2026, 8, 31, 13, tzinfo=KST)
    assert item.ends_at == datetime(2026, 8, 31, 14, tzinfo=KST)


def test_priority_is_already_reflected_in_total_score() -> None:
    lower = _candidate(0.4, lat=33.5001)
    boosted = _candidate(0.9, lat=33.5001)

    result = build(
        [lower, boosted],
        _request(),
        lambda *_args: RouteLeg(distance_m=10, duration_min=1, polyline=None),
    )

    assert result.days[0].items[0].candidate.place_id == boosted.place_id


def test_score_density_balances_score_and_estimated_travel_time() -> None:
    nearby = _candidate(0.7, lat=33.5001, stay_minutes=60)
    faraway = _candidate(0.9, lat=34.0, stay_minutes=60)

    result = build(
        [faraway, nearby],
        _request(),
        lambda *_args: RouteLeg(distance_m=10, duration_min=1, polyline=None),
    )

    assert result.days[0].items[0].candidate.place_id == nearby.place_id


def test_day_with_stay_includes_outbound_and_return_moves() -> None:
    stay = RouteAnchor(
        name="애월 숙소",
        coord=(33.47, 126.32),
        item_type=ScheduleItemType.ACCOMMODATION,
    )
    request = _request()
    request = BuildRequest(
        start_at=request.start_at,
        end_at=request.end_at,
        pace=request.pace,
        transport=request.transport,
        start_coord=request.start_coord,
        day_start_anchors={request.start_at.date(): stay},
        day_end_anchors={request.start_at.date(): stay},
    )
    calls: list[tuple] = []

    def fake_route(*args):
        calls.append(args)
        return RouteLeg(distance_m=1000, duration_min=10, polyline=None)

    result = build([_candidate(0.9)], request, fake_route)
    day = result.days[0]

    assert day.start_anchor == stay
    assert day.end_anchor == stay
    assert len(day.items) == 1
    assert len(day.moves) == 2
    assert [call[:2] for call in calls] == [
        (stay.coord, (day.items[0].candidate.lat, day.items[0].candidate.lng)),
        ((day.items[0].candidate.lat, day.items[0].candidate.lng), stay.coord),
    ]


def test_last_day_can_start_at_stay_without_forcing_return() -> None:
    stay = RouteAnchor(
        name="성산 숙소",
        coord=(33.45, 126.92),
        item_type=ScheduleItemType.ACCOMMODATION,
    )
    request = _request()
    request = BuildRequest(
        start_at=request.start_at,
        end_at=request.end_at,
        pace=request.pace,
        transport=request.transport,
        start_coord=request.start_coord,
        day_start_anchors={request.start_at.date(): stay},
    )

    result = build(
        [_candidate(0.9)],
        request,
        lambda *_args: RouteLeg(distance_m=1000, duration_min=10, polyline=None),
    )

    assert result.days[0].start_anchor == stay
    assert result.days[0].end_anchor is None
    assert len(result.days[0].moves) == 1
