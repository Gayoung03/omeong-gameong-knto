"""여행 날짜별 예보를 weather_snapshots 로 저장하는 helpers.

`route_recommendation._save_itinerary` 가 하루마다 부른다. 이 모듈은 상위
orchestrator 를 import 하지 않는다(단방향).
"""

import uuid
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.db.models import WeatherSnapshot
from app.db.models.enums import WeatherCondition
from app.integrations.weather.kma import KST, DayForecast, region_key
from app.recommend.common.geo import Coordinate
from app.recommend.itinerary.plan import CLOUDY_POP, RAIN_POP


def _weather_region(coord: Coordinate) -> str:
    """기상청 5km 격자 키. weather_snapshots UNIQUE(region, forecast_at)의 region."""
    return region_key(coord[0], coord[1])


def _snapshot_condition(forecast: DayForecast) -> WeatherCondition:
    """일 단위 강수확률·기온으로 대표 날씨를 고른다(시간별 하늘/강수형태는 미보유).

    강수확률이 높으면 비/눈(영하), 중간이면 흐림, 낮으면 맑음으로 근사한다. 임계값은
    plan_day 의 규칙 상수(RAIN_POP·CLOUDY_POP)를 재사용한다.
    """
    if forecast.pop_max >= RAIN_POP:
        if forecast.tmin is not None and forecast.tmin <= 0:
            return WeatherCondition.SNOWY
        return WeatherCondition.RAINY
    if forecast.pop_max >= CLOUDY_POP:
        return WeatherCondition.CLOUDY
    return WeatherCondition.SUNNY


def _representative_temp(forecast: DayForecast) -> float | None:
    """스냅샷 대표 기온. 오후(15→14→13시 순) 기온을 우선, 없으면 최고기온."""
    for hour in (15, 14, 13):
        if hour in forecast.hourly_tmp:
            return forecast.hourly_tmp[hour]
    if forecast.tmax is not None:
        return forecast.tmax
    return max(forecast.hourly_tmp.values(), default=None)


def _upsert_weather_snapshot(
    db: Session, region: str, coord: Coordinate, route_date: date, forecast: DayForecast
) -> uuid.UUID:
    """그날 예보를 weather_snapshots 에 upsert 하고 id 를 돌려준다.

    region 은 격자 키, forecast_at 은 그날 00:00 KST. 같은 격자·날짜를 동시에 생성하는
    두 요청이 겹쳐도 SELECT→INSERT 는 UNIQUE(region, forecast_at) IntegrityError 로
    정상 일정을 FAILED 로 만든다. 저장소 첫 ON CONFLICT 도입 — 원자적 upsert 로 막는다.
    """
    forecast_at = datetime.combine(route_date, time(0, 0), tzinfo=KST)
    temperature = _representative_temp(forecast)
    mutable = {
        "latitude": Decimal(str(coord[0])),
        "longitude": Decimal(str(coord[1])),
        "condition": _snapshot_condition(forecast),
        "temperature": None if temperature is None else Decimal(str(round(temperature, 1))),
        "min_temperature": (
            None if forecast.tmin is None else Decimal(str(round(forecast.tmin, 1)))
        ),
        "max_temperature": (
            None if forecast.tmax is None else Decimal(str(round(forecast.tmax, 1)))
        ),
        "precipitation_probability": forecast.pop_max,
        "source_updated_at": datetime.now(KST),
    }
    statement = (
        pg_insert(WeatherSnapshot)
        .values(id=uuid.uuid4(), region=region, forecast_at=forecast_at, **mutable)
        .on_conflict_do_update(index_elements=["region", "forecast_at"], set_=mutable)
        .returning(WeatherSnapshot.id)
    )
    return db.execute(statement).scalar_one()
