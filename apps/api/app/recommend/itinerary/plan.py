"""하루의 슬롯 계획.

날씨·기온 예보와 여행 속도 규칙으로 그날의 슬롯 구성(활동/점심/저녁 개수와
시간대·환경 선호)을 정한다. 순수 함수라 예보만 주면 결과가 결정된다. 실제
채우기(그리디)와 시각 계산은 build 가 맡는다.

날씨 규칙(route-redesign §2.1·routes.md 개정 2026-09-07):
- 비: 강수확률이 높으면 그날 활동의 실내 비중을 올린다. 60~80% 는 활동의 과반을
  **앞쪽부터** 실내 선호로 둔다 — 오전을 실내로 시작하면 오후에 개었을 때 실외로
  바꾸기 쉽다. 80% 이상이면 활동 전부를 실내 선호로 둔다.
- 더위: 최고기온이 높으면 정오~오후 3시에 걸치는 실외 방문을 피한다(판정은 build 가
  후보의 예상 방문 구간으로 한다).
- 예보 범위(3일) 밖이거나 조회 실패면 규칙을 적용하지 않는다("중립"이 아니라 "미적용").
둘 다 선호(preference)라 후보가 부족하면 완화 사다리에서 풀린다.
"""

import math
from dataclasses import dataclass
from datetime import datetime, time
from typing import Literal

from app.db.models.enums import PlaceEnvironment, ScheduleItemType
from app.integrations.weather.kma import DayForecast
from app.recommend.config.pace import PaceRule

from .types import DINNER_START, DINNER_START_BY, LUNCH_START, LUNCH_START_BY

#: 강수확률(%): 이 값 이상이면 흐림으로 본다(스냅샷 condition).
CLOUDY_POP = 30
#: 강수확률(%): 이 값 이상이면 활동 과반을 실내 선호로(스냅샷 condition 에선 비).
RAIN_POP = 60
#: 강수확률(%): 이 값 이상이면 활동 전부를 실내 선호로.
HEAVY_RAIN_POP = 80
#: 최고기온(℃): 이 값 이상이면 정오~15시 실외 방문 회피.
HEAT_TMAX = 30.0

SlotKind = Literal["activity", "lunch", "dinner"]


@dataclass(frozen=True)
class DaySlot:
    """하루 안의 한 자리. build 가 순서대로(식사는 시각 트리거로) 채운다."""

    kind: SlotKind
    required_type: ScheduleItemType | None = None
    earliest: time | None = None  # 방문 시작 하한(not_before)
    latest: time | None = None  # 방문 시작 상한(start_by)
    env_preference: PlaceEnvironment | None = None
    avoid_outdoor_midday: bool = False


def plan_day(
    day_start: datetime,
    day_end: datetime,
    pace_rule: PaceRule,
    forecast: DayForecast | None,
    *,
    restaurant_preferred: bool,
    indoor_bias: bool = False,
) -> list[DaySlot]:
    """그날의 슬롯 구성을 시간·환경 속성과 함께 만든다."""

    places = pace_rule["places_per_day"]
    dinner_required = day_end.time() >= DINNER_START
    lunch_required = (
        restaurant_preferred
        and not dinner_required
        and day_start.time() <= LUNCH_START_BY
        and day_end.time() >= LUNCH_START
    )
    has_meal = dinner_required or lunch_required
    activity_count = max(places - 1 if has_meal else places, 0)

    indoor_count, hot = _weather_envs(activity_count, forecast, indoor_bias)
    slots: list[DaySlot] = [
        DaySlot(
            kind="activity",
            env_preference=PlaceEnvironment.INDOOR if index < indoor_count else None,
            avoid_outdoor_midday=hot,
        )
        for index in range(activity_count)
    ]
    if dinner_required:
        slots.append(
            DaySlot("dinner", ScheduleItemType.RESTAURANT, DINNER_START, DINNER_START_BY)
        )
    elif lunch_required:
        slots.append(DaySlot("lunch", ScheduleItemType.RESTAURANT, LUNCH_START, LUNCH_START_BY))
    return slots


def _weather_envs(
    activity_count: int, forecast: DayForecast | None, indoor_bias: bool
) -> tuple[int, bool]:
    """(실내 선호로 둘 앞쪽 활동 수, 더위 회피 여부)."""

    pop = forecast.pop_max if forecast is not None else None
    tmax = forecast.tmax if forecast is not None else None
    if indoor_bias or (pop is not None and pop >= HEAVY_RAIN_POP):
        indoor_count = activity_count
    elif pop is not None and pop >= RAIN_POP:
        indoor_count = math.ceil(activity_count / 2)
    else:
        indoor_count = 0
    hot = tmax is not None and tmax >= HEAT_TMAX
    return indoor_count, hot
