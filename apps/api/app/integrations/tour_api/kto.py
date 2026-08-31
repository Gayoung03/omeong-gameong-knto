"""한국관광공사 TourAPI를 추천 요청 시점에만 조회한다."""

from dataclasses import dataclass
from urllib.parse import unquote

import httpx

from app.core.config import settings

LOCATION_LIST_URL = "https://apis.data.go.kr/B551011/KorPetTourService2/locationBasedList2"
REQUEST_TIMEOUT_SECONDS = 10.0


class TourAPIError(RuntimeError):
    """TourAPI를 조회하거나 응답을 해석하지 못했다."""


@dataclass(frozen=True)
class TourPlace:
    content_id: str
    title: str
    latitude: float
    longitude: float
    content_type_id: str | None = None
    address: str | None = None
    image_url: str | None = None


def get_nearby_places(
    latitude: float,
    longitude: float,
    *,
    radius_m: int = 20_000,
    limit: int = 100,
    client: httpx.Client | None = None,
) -> list[TourPlace]:
    """좌표 주변 관광정보를 실시간 조회한다. 응답은 저장하거나 캐시하지 않는다."""

    if not settings.tour_api_key:
        raise TourAPIError("TOUR_API_KEY가 설정되지 않았습니다")
    params = {
        "serviceKey": unquote(settings.tour_api_key),
        "MobileOS": "ETC",
        "MobileApp": "OmeongGameong",
        "_type": "json",
        "mapX": longitude,
        "mapY": latitude,
        "radius": radius_m,
        "numOfRows": limit,
        "pageNo": 1,
        "arrange": "E",
    }
    try:
        if client is None:
            with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as owned_client:
                response = owned_client.get(LOCATION_LIST_URL, params=params)
        else:
            response = client.get(LOCATION_LIST_URL, params=params)
        response.raise_for_status()
        payload = response.json()["response"]
        header = payload["header"]
        if str(header.get("resultCode")) not in {"0000", "00"}:
            raise TourAPIError(f"TourAPI 오류: {header.get('resultMsg', '알 수 없는 오류')}")
        items_container = payload.get("body", {}).get("items", {})
        raw_items = items_container.get("item", []) if isinstance(items_container, dict) else []
    except TourAPIError:
        raise
    except httpx.HTTPStatusError as error:
        raise TourAPIError(
            f"TourAPI HTTP 요청이 거절됐습니다({error.response.status_code})"
        ) from None
    except (httpx.HTTPError, KeyError, TypeError, ValueError):
        # HTTP 예외 문자열에는 serviceKey가 포함된 URL이 들어갈 수 있어
        # 원본 예외를 연결하거나 로그에 남기지 않는다.
        raise TourAPIError("TourAPI 관광정보 조회에 실패했습니다") from None

    if isinstance(raw_items, dict):
        raw_items = [raw_items]
    if not isinstance(raw_items, list):
        return []

    result: list[TourPlace] = []
    for item in raw_items:
        try:
            place = TourPlace(
                content_id=str(item["contentid"]),
                title=str(item["title"]).strip(),
                latitude=float(item["mapy"]),
                longitude=float(item["mapx"]),
                content_type_id=(
                    str(item.get("contenttypeid")).strip()
                    if item.get("contenttypeid") not in (None, "")
                    else None
                ),
                address=(str(item.get("addr1") or "").strip() or None),
                image_url=(str(item.get("firstimage") or "").strip() or None),
            )
        except (KeyError, TypeError, ValueError):
            continue
        if place.title and -90 <= place.latitude <= 90 and -180 <= place.longitude <= 180:
            result.append(place)
    return result
