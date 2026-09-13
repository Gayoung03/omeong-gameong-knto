from datetime import datetime
from zoneinfo import ZoneInfo

from app.db.models.enums import PlaceEnvironment, ScheduleItemType
from app.integrations.weather.kma import DayForecast
from app.recommend.config.pace import PACE
from app.recommend.itinerary.plan import plan_day

KST = ZoneInfo("Asia/Seoul")
NORMAL = PACE["normal"]  # places_per_day=4, window 09~19


def _day(start_hour: int, end_hour: int) -> tuple[datetime, datetime]:
    return (
        datetime(2026, 8, 31, start_hour, tzinfo=KST),
        datetime(2026, 8, 31, end_hour, tzinfo=KST),
    )


def _kinds(slots) -> list[str]:
    return [slot.kind for slot in slots]


def test_dinner_day_reserves_last_slot_for_restaurant() -> None:
    start, end = _day(9, 19)
    slots = plan_day(start, end, NORMAL, None, restaurant_preferred=False)

    assert _kinds(slots) == ["activity", "activity", "activity", "dinner"]
    assert slots[-1].required_type == ScheduleItemType.RESTAURANT


def test_lunch_day_adds_restaurant_when_preferred_and_ends_early() -> None:
    start, end = _day(9, 15)
    slots = plan_day(start, end, NORMAL, None, restaurant_preferred=True)

    assert _kinds(slots) == ["activity", "activity", "activity", "lunch"]


def test_no_meal_when_ends_early_without_restaurant_preference() -> None:
    start, end = _day(9, 15)
    slots = plan_day(start, end, NORMAL, None, restaurant_preferred=False)

    assert _kinds(slots) == ["activity"] * 4


def test_no_forecast_leaves_env_rules_off() -> None:
    start, end = _day(9, 15)
    slots = plan_day(start, end, NORMAL, None, restaurant_preferred=False)

    assert all(slot.env_preference is None for slot in slots)
    assert all(slot.avoid_outdoor_midday is False for slot in slots)


def test_rain_between_sixty_and_eighty_marks_front_half_indoor() -> None:
    start, end = _day(9, 15)  # 활동 4개
    forecast = DayForecast(pop_max=70, tmax=25.0, tmin=20.0, hourly_tmp={})

    slots = plan_day(start, end, NORMAL, forecast, restaurant_preferred=False)

    prefs = [slot.env_preference for slot in slots]
    assert prefs == [PlaceEnvironment.INDOOR, PlaceEnvironment.INDOOR, None, None]


def test_heavy_rain_marks_all_activities_indoor() -> None:
    start, end = _day(9, 15)
    forecast = DayForecast(pop_max=85, tmax=25.0, tmin=20.0, hourly_tmp={})

    slots = plan_day(start, end, NORMAL, forecast, restaurant_preferred=False)

    assert all(slot.env_preference == PlaceEnvironment.INDOOR for slot in slots)


def test_heat_marks_activities_to_avoid_midday_outdoor() -> None:
    start, end = _day(9, 15)
    forecast = DayForecast(pop_max=10, tmax=31.0, tmin=24.0, hourly_tmp={})

    slots = plan_day(start, end, NORMAL, forecast, restaurant_preferred=False)

    assert all(slot.avoid_outdoor_midday for slot in slots)
    assert all(slot.env_preference is None for slot in slots)


def test_indoor_bias_forces_all_indoor_without_forecast() -> None:
    start, end = _day(9, 15)
    slots = plan_day(start, end, NORMAL, None, restaurant_preferred=False, indoor_bias=True)

    assert all(slot.env_preference == PlaceEnvironment.INDOOR for slot in slots)
