import uuid
from datetime import datetime, time
from zoneinfo import ZoneInfo

from app.db.models.enums import TransportType, TripPace
from app.recommend.itinerary import BuildRequest, build
from app.recommend.schemas import BusinessHour, ScoredCandidate
from app.recommend.tmap import RouteLeg

KST = ZoneInfo("Asia/Seoul")


def _candidate(
    score: float,
    *,
    lat: float = 33.4996,
    lng: float = 126.5312,
    stay_minutes: int = 60,
    business_hours: list[BusinessHour] | None = None,
) -> ScoredCandidate:
    return ScoredCandidate(
        place_id=uuid.uuid4(),
        lat=lat,
        lng=lng,
        item_type="attraction",
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
        _candidate(score, lat=33.5 + index / 1000)
        for index, score in enumerate((0.9, 0.8, 0.7, 0.6))
    ]
    calls: list[tuple] = []

    def fake_route(*args):
        calls.append(args)
        return RouteLeg(distance_m=1000, duration_min=10, polyline=None)

    result = build(candidates, _request(TripPace.RELAXED), fake_route)

    assert len(result.days[0].items) == 3
    assert len(calls) == 3
    assert len(result.days[0].moves) == 2
    assert result.days[0].items[0].starts_at == datetime(2026, 8, 31, 10, 10, tzinfo=KST)
    assert result.days[0].items[1].starts_at == datetime(2026, 8, 31, 12, tzinfo=KST)


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
