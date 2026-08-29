"""카카오 주소 검색 API를 이용한 좌표 변환."""

from dataclasses import dataclass

import httpx

from app.core.config import settings

KAKAO_ADDRESS_URL = "https://dapi.kakao.com/v2/local/search/address.json"
REQUEST_TIMEOUT_SECONDS = 10.0


class KakaoGeocodingError(RuntimeError):
    """주소를 좌표로 바꾸지 못했다."""


@dataclass(frozen=True)
class GeocodedAddress:
    latitude: float
    longitude: float
    address_name: str


def geocode_address(
    address: str,
    *,
    client: httpx.Client | None = None,
) -> GeocodedAddress:
    """주소의 첫 번째 검색 결과를 WGS84 위도·경도로 반환한다."""

    query = address.strip()
    if not query:
        raise KakaoGeocodingError("변환할 주소가 비어 있습니다")
    if not settings.kakao_rest_api_key:
        raise KakaoGeocodingError("KAKAO_REST_API_KEY가 설정되지 않았습니다")

    headers = {"Authorization": f"KakaoAK {settings.kakao_rest_api_key}"}
    try:
        if client is None:
            with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as owned_client:
                response = owned_client.get(
                    KAKAO_ADDRESS_URL,
                    headers=headers,
                    params={"query": query, "size": 1},
                )
        else:
            response = client.get(
                KAKAO_ADDRESS_URL,
                headers=headers,
                params={"query": query, "size": 1},
            )
        response.raise_for_status()
        body = response.json()
    except (httpx.HTTPError, ValueError) as error:
        raise KakaoGeocodingError("카카오 주소 검색에 실패했습니다") from error

    documents = body.get("documents") if isinstance(body, dict) else None
    if not isinstance(documents, list) or not documents:
        raise KakaoGeocodingError("주소에 해당하는 좌표를 찾지 못했습니다")

    first = documents[0]
    try:
        latitude = float(first["y"])
        longitude = float(first["x"])
        address_name = str(first["address_name"])
    except (KeyError, TypeError, ValueError) as error:
        raise KakaoGeocodingError("카카오 주소 검색 응답 형식이 올바르지 않습니다") from error

    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise KakaoGeocodingError("카카오 주소 검색 좌표가 유효하지 않습니다")
    return GeocodedAddress(latitude, longitude, address_name)
