"""기상청 단기예보 강수확률 조회 테스트."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

import httpx
import pytest

from app.core.config import settings
from app.integrations.weather.kma import _to_grid, get_precipitation_probabilities

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
