import logging
import uuid
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from app.db.models.enums import ScheduleItemType, TransportType, TripPace
from app.recommend.itinerary import (
    DINNER_START,
    DINNER_START_BY,
    LUNCH_START,
    LUNCH_START_BY,
    MAX_TMAP_CALLS_PER_DAY,
    BuildRequest,
    RouteAnchor,
    build,
)
from app.recommend.schemas import BusinessHour, CandidateTier, ScoredCandidate
from app.recommend.tmap import RouteLeg, TMapError

KST = ZoneInfo("Asia/Seoul")


def _candidate(
    score: float,
    *,
    item_type: ScheduleItemType = ScheduleItemType.ATTRACTION,
    lat: float = 33.4996,
    lng: float = 126.5312,
    stay_minutes: int = 60,
    business_hours: list[BusinessHour] | None = None,
    source_category: str | None = None,
    tags: list[str] | None = None,
    tier: CandidateTier = CandidateTier.VERIFIED,
) -> ScoredCandidate:
    return ScoredCandidate(
        place_id=uuid.uuid4(),
        lat=lat,
        lng=lng,
        item_type=item_type,
        source_category=source_category,
        environment="outdoor",
        average_stay_minutes=stay_minutes,
        business_hours=business_hours or [],
        tags=tags or [],
        tier=tier,
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


def test_daily_tmap_calls_are_capped_and_fall_back_to_estimates(caplog) -> None:
    # 저녁 없는 짧은 하루 — 식사 슬롯 없이 관광 후보만 계속 걸러지는 상황을 만든다.
    request = BuildRequest(
        start_at=datetime(2026, 8, 31, 9, tzinfo=KST),
        end_at=datetime(2026, 8, 31, 16, tzinfo=KST),
        pace=TripPace.NORMAL,
        transport=TransportType.RENTAL_CAR,
        start_coord=(33.5, 126.53),
    )
    # 서로 가까워 추정 이동시간으로는 모두 통과하지만, 실제(가짜) TMAP 시간은
    # 하루 창을 넘겨 매번 _fit_visit 에서 탈락하는 후보들.
    candidates = [
        _candidate(0.9 - index / 1000, lat=33.5 + index / 5000) for index in range(20)
    ]
    calls: list[tuple] = []

    def slow_route(*args):
        calls.append(args)
        return RouteLeg(distance_m=100_000, duration_min=600, polyline=None)

    with caplog.at_level(logging.WARNING, logger="app.recommend.itinerary"):
        result = build(candidates, request, slow_route)

    # 상한까지만 실제 호출하고, 그 뒤 구간은 추정으로 일정을 완성한다.
    assert len(calls) == MAX_TMAP_CALLS_PER_DAY
    assert len(result.days[0].items) == 4  # normal pace: places_per_day
    # cap_logged 가드가 살아 경고는 정확히 한 번만 남는다.
    cap_logs = [r for r in caplog.records if "TMAP 호출 상한" in r.message]
    assert len(cap_logs) == 1


def test_tmap_call_cap_resets_each_day() -> None:
    # 마지막 날만 저녁 없이 끝나도록 이틀 여행을 구성한다. 카운터가 날마다 리셋되면
    # 2일차에서도 상한만큼 실제 호출이 다시 일어난다.
    request = BuildRequest(
        start_at=datetime(2026, 8, 31, 9, tzinfo=KST),
        end_at=datetime(2026, 9, 1, 16, tzinfo=KST),
        pace=TripPace.NORMAL,
        transport=TransportType.RENTAL_CAR,
        start_coord=(33.5, 126.53),
    )
    candidates = [
        _candidate(0.9 - index / 1000, lat=33.5 + index / 5000) for index in range(40)
    ]
    calls: list[tuple] = []

    def slow_route(*args):
        calls.append(args)
        return RouteLeg(distance_m=100_000, duration_min=600, polyline=None)

    result = build(candidates, request, slow_route)

    assert len(calls) == MAX_TMAP_CALLS_PER_DAY * 2
    assert result.days[0].items
    assert result.days[1].items


def test_cap_counts_only_real_tmap_calls_not_cache_hits() -> None:
    # 캐시 적중 레그(source="cache")는 상한에 세지 않는다. 20회를 넘겨도 상한에
    # 안 걸려, (여기선 모두 시간 초과로 탈락하는) 후보 전체를 끝까지 시도한다.
    request = BuildRequest(
        start_at=datetime(2026, 8, 31, 9, tzinfo=KST),
        end_at=datetime(2026, 8, 31, 16, tzinfo=KST),
        pace=TripPace.NORMAL,
        transport=TransportType.RENTAL_CAR,
        start_coord=(33.5, 126.53),
    )
    candidates = [
        _candidate(0.9 - index / 1000, lat=33.5 + index / 5000) for index in range(25)
    ]
    calls: list[tuple] = []

    def cache_route(*args):
        calls.append(args)
        return RouteLeg(distance_m=100_000, duration_min=600, polyline=None, source="cache")

    result = build(candidates, request, cache_route)

    assert len(calls) == 25  # > MAX_TMAP_CALLS_PER_DAY 인데도 상한에 안 걸림
    assert result.days[0].items == ()


def test_tmap_error_disables_real_calls_for_whole_trip(caplog) -> None:
    # 첫 호출이 TMapError 를 내면 여행 전체에서 실제 호출을 끄고 추정으로 진행한다.
    request = BuildRequest(
        start_at=datetime(2026, 8, 31, 9, tzinfo=KST),
        end_at=datetime(2026, 9, 1, 16, tzinfo=KST),
        pace=TripPace.NORMAL,
        transport=TransportType.RENTAL_CAR,
        start_coord=(33.5, 126.53),
    )
    candidates = [
        _candidate(0.9 - index / 1000, lat=33.5 + index / 5000) for index in range(10)
    ]
    calls: list[tuple] = []

    def failing_route(*args):
        calls.append(args)
        raise TMapError("TMAP 다운")

    with caplog.at_level(logging.WARNING, logger="app.recommend.itinerary"):
        result = build(candidates, request, failing_route)

    # 첫 오류 한 번만 실제로 호출하고, 이후 모든 날짜는 추정으로 채운다.
    assert len(calls) == 1
    assert result.days[0].items
    assert result.days[1].items
    error_logs = [r for r in caplog.records if "TMAP 조회 실패" in r.message]
    assert len(error_logs) == 1


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


def test_similar_coastal_places_are_not_recommended_consecutively() -> None:
    first_beach = _candidate(0.99, source_category="beach", lat=33.501)
    second_beach = _candidate(0.98, source_category="beach", lat=33.502)
    museum = _candidate(0.7, source_category="attraction", tags=["indoor_tourism"], lat=33.503)
    dinner = _candidate(
        0.6,
        item_type=ScheduleItemType.RESTAURANT,
        source_category="restaurant",
        lat=33.504,
    )

    result = build(
        [first_beach, second_beach, museum, dinner],
        _request(TripPace.RELAXED),
        lambda *_args: RouteLeg(distance_m=1000, duration_min=10, polyline=None),
    )

    non_meals = [
        item
        for item in result.days[0].items
        if item.candidate.item_type != ScheduleItemType.RESTAURANT
    ]
    assert [item.candidate.source_category for item in non_meals] == ["beach", "attraction"]


def test_coastal_daily_limit_is_relaxed_only_when_candidates_are_insufficient() -> None:
    beaches = [
        _candidate(0.9 - index / 100, source_category="beach", lat=33.501 + index / 1000)
        for index in range(2)
    ]
    dinner = _candidate(
        0.6,
        item_type=ScheduleItemType.RESTAURANT,
        source_category="restaurant",
        lat=33.51,
    )

    result = build(
        [*beaches, dinner],
        _request(TripPace.RELAXED),
        lambda *_args: RouteLeg(distance_m=1000, duration_min=10, polyline=None),
    )

    assert sum(item.candidate.source_category == "beach" for item in result.days[0].items) == 2


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


def test_dinner_starts_by_half_past_seven_even_when_long_attraction_scores_higher() -> None:
    long_attraction = _candidate(0.99, stay_minutes=480)
    dinner = _candidate(0.5, item_type=ScheduleItemType.RESTAURANT)

    result = build(
        [long_attraction, dinner],
        _request(TripPace.NORMAL),
        lambda *_args: RouteLeg(distance_m=1000, duration_min=10, polyline=None),
    )

    day = result.days[0]
    assert day.items[-1].candidate.item_type == ScheduleItemType.RESTAURANT
    assert DINNER_START <= day.items[-1].starts_at.time() <= DINNER_START_BY


def test_restaurant_preference_adds_lunch_when_trip_ends_before_dinner() -> None:
    request = BuildRequest(
        start_at=datetime(2026, 8, 31, 9, tzinfo=KST),
        end_at=datetime(2026, 8, 31, 15, tzinfo=KST),
        pace=TripPace.NORMAL,
        transport=TransportType.RENTAL_CAR,
        start_coord=(33.5, 126.53),
        restaurant_preferred=True,
    )
    candidates = [
        _candidate(0.9, lat=33.501),
        _candidate(0.8, item_type=ScheduleItemType.RESTAURANT, lat=33.502),
        _candidate(0.7, lat=33.503),
    ]

    result = build(
        candidates,
        request,
        lambda *_args: RouteLeg(distance_m=1000, duration_min=10, polyline=None),
    )

    day = result.days[0]
    lunch = next(
        item for item in day.items if item.candidate.item_type == ScheduleItemType.RESTAURANT
    )
    assert day.dinner_required is False
    assert day.restaurant_required is True
    assert LUNCH_START <= lunch.starts_at.time() <= LUNCH_START_BY


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


# ---------------------------------------------------------------------------
# 부분 성공: 빈 슬롯 · 확인 필요 폴백 · 대안 후보
# ---------------------------------------------------------------------------


def _fast_route(*_args):
    return RouteLeg(distance_m=1000, duration_min=10, polyline=None)


def test_no_restaurant_leaves_unfilled_dinner_slot() -> None:
    # 저녁이 필요한데 식당 후보가 하나도 없으면 실패가 아니라 빈 저녁 슬롯으로 남긴다.
    attractions = [_candidate(0.9 - index / 100, lat=33.5 + index / 1000) for index in range(5)]

    result = build(attractions, _request(TripPace.NORMAL), _fast_route)
    day = result.days[0]

    assert day.dinner_required is True
    assert day.items  # 관광 일정은 정상 배치
    assert all(item.candidate.item_type == ScheduleItemType.ATTRACTION for item in day.items)
    assert len(day.unfilled) == 1
    assert day.unfilled[0].item_type == ScheduleItemType.RESTAURANT


def test_needs_check_taken_only_when_no_verified() -> None:
    request = BuildRequest(
        start_at=datetime(2026, 8, 31, 9, tzinfo=KST),
        end_at=datetime(2026, 8, 31, 15, tzinfo=KST),  # 저녁 없음
        pace=TripPace.NORMAL,
        transport=TransportType.RENTAL_CAR,
        start_coord=(33.5, 126.53),
    )
    verified = _candidate(0.5, lat=33.501, tier=CandidateTier.VERIFIED)
    needs_check = _candidate(0.9, lat=33.502, tier=CandidateTier.NEEDS_CHECK)

    result = build([needs_check, verified], request, _fast_route)
    day = result.days[0]

    # 점수는 needs_check 가 높지만 확실 후보를 먼저 쓴다.
    assert day.items[0].candidate.tier == CandidateTier.VERIFIED

    # 확실 후보가 아예 없으면 확인 필요 후보를 채택한다.
    only_needs_check = build(
        [_candidate(0.9, lat=33.503, tier=CandidateTier.NEEDS_CHECK)], request, _fast_route
    )
    assert only_needs_check.days[0].items[0].candidate.tier == CandidateTier.NEEDS_CHECK


def test_alternatives_capped_at_three_and_unique() -> None:
    request = BuildRequest(
        start_at=datetime(2026, 8, 31, 9, tzinfo=KST),
        end_at=datetime(2026, 8, 31, 15, tzinfo=KST),
        pace=TripPace.NORMAL,
        transport=TransportType.RENTAL_CAR,
        start_coord=(33.5, 126.53),
    )
    attractions = [_candidate(0.9 - index / 100, lat=33.5 + index / 2000) for index in range(6)]

    result = build(attractions, request, _fast_route)
    day = result.days[0]
    first = day.items[0]
    alternatives = day.alternatives[first.candidate.place_id]

    assert len(alternatives) <= 3
    ids = [candidate.place_id for candidate in alternatives]
    assert len(ids) == len(set(ids))  # 중복 없음
    assert first.candidate.place_id not in ids  # 자기 자신 제외


def test_evening_arrival_places_attractions_and_keeps_anchors() -> None:
    # 저녁 도착일(18:00 시작·식당 0): 실패가 아니라 관광 배치 + 빈 저녁 + 앵커 유지.
    trip_date = date(2026, 8, 31)
    stay = RouteAnchor(name="숙소", coord=(33.48, 126.33), item_type=ScheduleItemType.ACCOMMODATION)
    request = BuildRequest(
        start_at=datetime(2026, 8, 31, 18, tzinfo=KST),
        end_at=datetime(2026, 8, 31, 21, tzinfo=KST),
        pace=TripPace.PACKED,
        transport=TransportType.RENTAL_CAR,
        start_coord=(33.5, 126.53),
        day_start_anchors={trip_date: stay},
        day_end_anchors={trip_date: stay},
    )
    attractions = [_candidate(0.9 - index / 100, lat=33.5 + index / 1000) for index in range(5)]

    day = build(attractions, request, _fast_route).days[0]

    assert day.items
    assert len(day.unfilled) == 1
    assert day.unfilled[0].item_type == ScheduleItemType.RESTAURANT
    assert day.start_anchor == stay
    assert day.end_anchor == stay


def test_evening_arrival_with_no_places_still_keeps_anchors() -> None:
    trip_date = date(2026, 8, 31)
    stay = RouteAnchor(name="숙소", coord=(33.48, 126.33), item_type=ScheduleItemType.ACCOMMODATION)
    request = BuildRequest(
        start_at=datetime(2026, 8, 31, 18, tzinfo=KST),
        end_at=datetime(2026, 8, 31, 21, tzinfo=KST),
        pace=TripPace.PACKED,
        transport=TransportType.RENTAL_CAR,
        start_coord=(33.5, 126.53),
        day_start_anchors={trip_date: stay},
        day_end_anchors={trip_date: stay},
    )

    day = build([], request, _fast_route).days[0]

    assert day.items == ()
    assert len(day.unfilled) == 1
    assert day.start_anchor == stay  # 빈 슬롯만 있어도 앵커는 남는다
    assert day.end_anchor == stay


def test_packed_lunch_preference_records_unfilled_when_no_restaurant() -> None:
    # packed + 맛집 선호: 짧은 방문으로 슬롯이 다 차도 점심을 시도/빈 슬롯으로 남긴다.
    request = BuildRequest(
        start_at=datetime(2026, 8, 31, 8, tzinfo=KST),
        end_at=datetime(2026, 8, 31, 15, tzinfo=KST),  # 저녁 아님 → 점심 선호
        pace=TripPace.PACKED,
        transport=TransportType.RENTAL_CAR,
        start_coord=(33.5, 126.53),
        restaurant_preferred=True,
    )
    attractions = [_candidate(0.9 - index / 100, lat=33.5 + index / 1000) for index in range(5)]

    day = build(attractions, request, _fast_route).days[0]

    assert day.restaurant_required is True
    assert len(day.unfilled) == 1
    assert day.unfilled[0].item_type == ScheduleItemType.RESTAURANT


def test_safety_net_records_meal_when_loop_ends_early() -> None:
    # 후보 소진으로 식사 슬롯을 시도하기 전에 루프가 끝나도 빈 식사 슬롯을 남긴다.
    day = build([_candidate(0.9)], _request(TripPace.NORMAL), _fast_route).days[0]

    assert len(day.items) == 1
    assert len(day.unfilled) == 1
    assert day.unfilled[0].item_type == ScheduleItemType.RESTAURANT


def test_unfilled_slot_candidates_are_needs_check_restaurants_sorted() -> None:
    dow = (date(2026, 8, 31).weekday() + 1) % 7
    closed = [BusinessHour(day_of_week=dow, is_closed=True)]
    attraction = _candidate(0.95, lat=33.501)
    restaurants = [
        _candidate(
            score,
            item_type=ScheduleItemType.RESTAURANT,
            lat=33.5 + index / 1000,
            business_hours=closed,
            tier=CandidateTier.NEEDS_CHECK,
        )
        for index, score in enumerate((0.3, 0.8, 0.5, 0.6))
    ]

    day = build([attraction, *restaurants], _request(TripPace.NORMAL), _fast_route).days[0]

    assert len(day.unfilled) == 1
    candidates = day.unfilled[0].candidates
    assert all(candidate.tier == CandidateTier.NEEDS_CHECK for candidate in candidates)
    assert all(candidate.item_type == ScheduleItemType.RESTAURANT for candidate in candidates)
    assert len(candidates) == 3  # 4개 중 상위 3
    assert [candidate.total_score for candidate in candidates] == [0.8, 0.6, 0.5]
