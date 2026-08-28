"""카카오 주소 좌표 변환 단위 테스트."""

import httpx
import pytest

from app.core.config import settings
from app.integrations.maps.kakao import KakaoGeocodingError, geocode_address


def test_geocode_address_uses_rest_key_and_returns_lat_lng(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "kakao_rest_api_key", "test-key")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "KakaoAK test-key"
        assert request.url.params["query"] == "제주시 애월읍"
        assert request.url.params["size"] == "1"
        return httpx.Response(
            200,
            json={
                "documents": [{"x": "126.3112", "y": "33.4622", "address_name": "제주시 애월읍"}]
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = geocode_address(" 제주시 애월읍 ", client=client)

    assert result.longitude == 126.3112
    assert result.latitude == 33.4622


def test_geocode_address_rejects_empty_result(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "kakao_rest_api_key", "test-key")

    with httpx.Client(
        transport=httpx.MockTransport(lambda _request: httpx.Response(200, json={"documents": []}))
    ) as client:
        with pytest.raises(KakaoGeocodingError, match="찾지 못했습니다"):
            geocode_address("없는 주소", client=client)
