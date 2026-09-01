"""홈 화면 현재 날씨 엔드포인트."""

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.db.models.enums import WeatherCondition
from app.integrations.weather.kma import WeatherForecastError, get_current_weather
from app.schemas.base import APISchema

router = APIRouter()


class WeatherRegion(StrEnum):
    JEJU = "제주"
    SEOGWIPO = "서귀포"
    HALLIM = "한림"
    SEONGSAN = "성산"


REGION_COORDINATES = {
    WeatherRegion.JEJU: (33.4996, 126.5312),
    WeatherRegion.SEOGWIPO: (33.2541, 126.5601),
    WeatherRegion.HALLIM: (33.4100, 126.2687),
    WeatherRegion.SEONGSAN: (33.4505, 126.9248),
}


class CurrentWeatherResponse(APISchema):
    region: WeatherRegion
    forecast_at: datetime
    condition: WeatherCondition
    temperature: float
    precipitation_probability: int
    humidity: int
    wind_speed: float
    source_updated_at: datetime


@router.get(
    "/weather/current",
    response_model=CurrentWeatherResponse,
    summary="제주 권역 현재 날씨",
)
def current_weather(
    region: Annotated[WeatherRegion, Query(description="제주·서귀포·한림·성산")],
) -> CurrentWeatherResponse:
    latitude, longitude = REGION_COORDINATES[region]
    try:
        weather = get_current_weather(latitude, longitude)
    except WeatherForecastError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error),
        ) from error

    return CurrentWeatherResponse(
        region=region,
        forecast_at=weather.forecast_at,
        condition=weather.condition,
        temperature=weather.temperature,
        precipitation_probability=weather.precipitation_probability,
        humidity=weather.humidity,
        wind_speed=weather.wind_speed,
        source_updated_at=weather.source_updated_at,
    )
