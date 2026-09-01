"""기상청 단기예보 강수확률 조회 테스트."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints import weather as weather_endpoint
from app.core.config import settings
from app.integrations.weather.kma import (
    CurrentWeather,
    _to_grid,
    get_current_weather,
    get_precipitation_probabilities,
)
from app.main import app

KST = ZoneInfo("Asia/Seoul")


def test_jeju_airport_coordinate_converts_to_kma_grid() -> None:
    assert _to_grid(33.505929, 126.495952) == (52, 38)


def test_forecast_returns_daily_max_precipitation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "weather_api_key", "decoded-key")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["serviceKey"] == "decoded-key"
        assert request.url.params["base_date"] == "20260828"
        assert request.url.params["base_time"] == "1400"
        assert request.url.params["nx"] == "52"
        assert request.url.params["ny"] == "38"
        return httpx.Response(
            200,
            json={
                "response": {
                    "header": {"resultCode": "00", "resultMsg": "NORMAL_SERVICE"},
                    "body": {
                        "items": {
                            "item": [
                                {"category": "POP", "fcstDate": "20260829", "fcstValue": "20"},
                                {"category": "POP", "fcstDate": "20260829", "fcstValue": "70"},
                                {"category": "TMP", "fcstDate": "20260829", "fcstValue": "25"},
                            ]
                        }
                    },
                }
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = get_precipitation_probabilities(
            33.505929,
            126.495952,
            {date(2026, 8, 29)},
            now=datetime(2026, 8, 28, 14, 30, tzinfo=KST),
            client=client,
        )

    assert result == {date(2026, 8, 29): 70}


def test_current_weather_uses_nearest_forecast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "weather_api_key", "decoded-key")

    def handler(request: httpx.Request) -> httpx.Response:
        items = []
        for forecast_time, temperature in (("1400", "23"), ("1500", "24.5")):
            values = {
                "TMP": temperature,
                "POP": "70",
                "REH": "82",
                "WSD": "4.2",
                "SKY": "4",
                "PTY": "1",
            }
            items.extend(
                {
                    "category": category,
                    "fcstDate": "20260828",
                    "fcstTime": forecast_time,
                    "fcstValue": value,
                }
                for category, value in values.items()
            )
        return httpx.Response(
            200,
            json={
                "response": {
                    "header": {"resultCode": "00", "resultMsg": "NORMAL_SERVICE"},
                    "body": {"items": {"item": items}},
                }
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = get_current_weather(
            33.4996,
            126.5312,
            now=datetime(2026, 8, 28, 14, 40, tzinfo=KST),
            client=client,
        )

    assert result.forecast_at == datetime(2026, 8, 28, 15, 0, tzinfo=KST)
    assert result.temperature == 24.5
    assert result.condition == "rainy"
    assert result.precipitation_probability == 70
    assert result.humidity == 82
    assert result.wind_speed == 4.2


def test_current_weather_endpoint_returns_camel_case(monkeypatch: pytest.MonkeyPatch) -> None:
    observed_coordinates: list[tuple[float, float]] = []

    def fake_current_weather(latitude: float, longitude: float) -> CurrentWeather:
        observed_coordinates.append((latitude, longitude))
        return CurrentWeather(
            forecast_at=datetime(2026, 8, 31, 15, 0, tzinfo=KST),
            condition="partly_cloudy",
            temperature=27.5,
            precipitation_probability=20,
            humidity=68,
            wind_speed=3.4,
            source_updated_at=datetime(2026, 8, 31, 14, 0, tzinfo=KST),
        )

    monkeypatch.setattr(weather_endpoint, "get_current_weather", fake_current_weather)

    with TestClient(app) as client:
        response = client.get("/api/v1/weather/current", params={"region": "한림"})

    assert response.status_code == 200
    assert observed_coordinates == [(33.4100, 126.2687)]
    assert response.json() == {
        "region": "한림",
        "forecastAt": "2026-08-31T15:00:00+09:00",
        "condition": "partly_cloudy",
        "temperature": 27.5,
        "precipitationProbability": 20,
        "humidity": 68,
        "windSpeed": 3.4,
        "sourceUpdatedAt": "2026-08-31T14:00:00+09:00",
    }
