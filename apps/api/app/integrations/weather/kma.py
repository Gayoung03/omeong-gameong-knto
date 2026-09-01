"""기상청 단기예보에서 현재 날씨와 여행 날짜별 강수확률을 조회한다."""

import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from urllib.parse import unquote
from zoneinfo import ZoneInfo

import httpx

from app.core.config import settings

KST = ZoneInfo("Asia/Seoul")
KMA_FORECAST_URL = "https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
BASE_HOURS = (2, 5, 8, 11, 14, 17, 20, 23)
REQUEST_TIMEOUT_SECONDS = 10.0


class WeatherForecastError(RuntimeError):
    """기상청 예보를 조회하거나 해석하지 못했다."""


@dataclass(frozen=True)
class CurrentWeather:
    forecast_at: datetime
    condition: str
    temperature: float
    precipitation_probability: int
    humidity: int
    wind_speed: float
    source_updated_at: datetime


def get_current_weather(
    latitude: float,
    longitude: float,
    *,
    now: datetime | None = None,
    client: httpx.Client | None = None,
) -> CurrentWeather:
    """좌표에서 현재 시각과 가장 가까운 단기예보를 반환한다."""

    current = (now or datetime.now(KST)).astimezone(KST)
    items, source_updated_at = _fetch_forecast_items(latitude, longitude, current, client)
    forecasts: dict[datetime, dict[str, str]] = {}
    for item in items:
        try:
            forecast_at = datetime.strptime(
                f"{item['fcstDate']}{item['fcstTime']}", "%Y%m%d%H%M"
            ).replace(tzinfo=KST)
            forecasts.setdefault(forecast_at, {})[item["category"]] = item["fcstValue"]
        except (KeyError, TypeError, ValueError):
            continue

    if not forecasts:
        raise WeatherForecastError("기상청 현재 예보가 비어 있습니다")

    forecast_at = min(forecasts, key=lambda value: abs(value - current))
    values = forecasts[forecast_at]
    try:
        temperature = float(values["TMP"])
        precipitation_probability = int(values["POP"])
        humidity = int(values["REH"])
        wind_speed = float(values["WSD"])
        condition = _weather_condition(values["SKY"], values["PTY"], wind_speed)
    except (KeyError, TypeError, ValueError) as error:
        raise WeatherForecastError("기상청 현재 예보 항목이 불완전합니다") from error

    return CurrentWeather(
        forecast_at=forecast_at,
        condition=condition,
        temperature=temperature,
        precipitation_probability=precipitation_probability,
        humidity=humidity,
        wind_speed=wind_speed,
        source_updated_at=source_updated_at,
    )


def get_precipitation_probabilities(
    latitude: float,
    longitude: float,
    dates: set[date],
    *,
    now: datetime | None = None,
    client: httpx.Client | None = None,
) -> dict[date, int]:
    """요청한 날짜마다 가장 높은 강수확률(POP)을 반환한다."""

    if not dates:
        return {}
    items, _ = _fetch_forecast_items(latitude, longitude, now or datetime.now(KST), client)

    result: dict[date, int] = {}
    for item in items:
        if item.get("category") != "POP":
            continue
        try:
            forecast_date = datetime.strptime(item["fcstDate"], "%Y%m%d").date()
            probability = int(item["fcstValue"])
        except (KeyError, TypeError, ValueError):
            continue
        if forecast_date in dates and 0 <= probability <= 100:
            result[forecast_date] = max(result.get(forecast_date, 0), probability)
    return result


def _fetch_forecast_items(
    latitude: float,
    longitude: float,
    now: datetime,
    client: httpx.Client | None,
) -> tuple[list[dict[str, str]], datetime]:
    if not settings.weather_api_key:
        raise WeatherForecastError("WEATHER_API_KEY가 설정되지 않았습니다")

    base_date, base_time = _latest_base(now)
    nx, ny = _to_grid(latitude, longitude)
    params = {
        "serviceKey": unquote(settings.weather_api_key),
        "pageNo": 1,
        "numOfRows": 1000,
        "dataType": "JSON",
        "base_date": base_date.strftime("%Y%m%d"),
        "base_time": f"{base_time:02d}00",
        "nx": nx,
        "ny": ny,
    }
    try:
        if client is None:
            with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as owned_client:
                response = owned_client.get(KMA_FORECAST_URL, params=params)
        else:
            response = client.get(KMA_FORECAST_URL, params=params)
        response.raise_for_status()
        body = response.json()
        header = body["response"]["header"]
        if header["resultCode"] != "00":
            raise WeatherForecastError(f"기상청 예보 오류: {header['resultMsg']}")
        items = body["response"]["body"]["items"]["item"]
        if not isinstance(items, list):
            raise WeatherForecastError("기상청 단기예보 항목이 비어 있습니다")
    except WeatherForecastError:
        raise
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as error:
        raise WeatherForecastError("기상청 단기예보 조회에 실패했습니다") from error

    source_updated_at = datetime.combine(
        base_date, datetime.min.time(), tzinfo=KST
    ) + timedelta(hours=base_time)
    return items, source_updated_at


def _weather_condition(sky: str, precipitation: str, wind_speed: float) -> str:
    if precipitation in {"3", "7"}:
        return "snowy"
    if precipitation != "0":
        return "rainy"
    if wind_speed >= 9:
        return "windy"
    return {"1": "sunny", "3": "partly_cloudy", "4": "cloudy"}[sky]


def _latest_base(now: datetime) -> tuple[date, int]:
    current = now.astimezone(KST) - timedelta(minutes=20)
    available = [hour for hour in BASE_HOURS if hour <= current.hour]
    if available:
        return current.date(), available[-1]
    return current.date() - timedelta(days=1), BASE_HOURS[-1]


def _to_grid(latitude: float, longitude: float) -> tuple[int, int]:
    """기상청 5km 격자 변환식으로 WGS84 위경도를 nx/ny로 바꾼다."""

    earth_radius = 6371.00877
    grid_size = 5.0
    first_standard_parallel = math.radians(30.0)
    second_standard_parallel = math.radians(60.0)
    origin_longitude = math.radians(126.0)
    origin_latitude = math.radians(38.0)
    origin_x, origin_y = 43.0, 136.0

    radius = earth_radius / grid_size
    sn = math.tan(math.pi * 0.25 + second_standard_parallel * 0.5) / math.tan(
        math.pi * 0.25 + first_standard_parallel * 0.5
    )
    sn = math.log(
        math.cos(first_standard_parallel) / math.cos(second_standard_parallel)
    ) / math.log(sn)
    sf = math.tan(math.pi * 0.25 + first_standard_parallel * 0.5) ** sn
    sf *= math.cos(first_standard_parallel) / sn
    ro = radius * sf / math.tan(math.pi * 0.25 + origin_latitude * 0.5) ** sn

    ra = radius * sf / math.tan(math.pi * 0.25 + math.radians(latitude) * 0.5) ** sn
    theta = math.radians(longitude) - origin_longitude
    if theta > math.pi:
        theta -= 2.0 * math.pi
    if theta < -math.pi:
        theta += 2.0 * math.pi
    theta *= sn
    x = math.floor(ra * math.sin(theta) + origin_x + 0.5)
    y = math.floor(ro - ra * math.cos(theta) + origin_y + 0.5)
    return x, y
