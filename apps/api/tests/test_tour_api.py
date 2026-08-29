import uuid

import httpx
import pytest

from app.core.config import settings
from app.db.models.enums import ScheduleItemType
from app.integrations.tour_api.kto import TourAPIError, TourPlace, get_nearby_places
from app.recommend.schemas import Candidate
from app.services.route_recommendation import _match_tour_places


def _client(payload: dict) -> httpx.Client:
    return httpx.Client(
        transport=httpx.MockTransport(lambda _request: httpx.Response(200, json=payload))
    )


def test_location_list_parses_tour_places(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "tour_api_key", "test-key")
    payload = {
        "response": {
            "header": {"resultCode": "0000", "resultMsg": "OK"},
            "body": {
                "items": {
                    "item": [
                        {
                            "contentid": "123",
                            "contenttypeid": "12",
                            "title": "함덕해수욕장",
                            "mapx": "126.6695",
                            "mapy": "33.5432",
                            "addr1": "제주시 조천읍",
                            "firstimage": "https://example.com/image.jpg",
                        }
                    ]
                }
            },
        }
    }

    with _client(payload) as client:
        places = get_nearby_places(33.5, 126.5, client=client)

    assert places == [
        TourPlace(
            content_id="123",
            content_type_id="12",
            title="함덕해수욕장",
            latitude=33.5432,
            longitude=126.6695,
            address="제주시 조천읍",
            image_url="https://example.com/image.jpg",
        )
    ]


def test_tour_api_error_is_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "tour_api_key", "test-key")
    payload = {
        "response": {
            "header": {"resultCode": "22", "resultMsg": "LIMIT EXCEEDED"},
            "body": {},
        }
    }

    with _client(payload) as client, pytest.raises(TourAPIError, match="LIMIT EXCEEDED"):
        get_nearby_places(33.5, 126.5, client=client)


def test_http_error_does_not_expose_service_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "tour_api_key", "secret-service-key")
    client = httpx.Client(
        transport=httpx.MockTransport(lambda _request: httpx.Response(403, text="forbidden"))
    )

    with client, pytest.raises(TourAPIError) as captured:
        get_nearby_places(33.5, 126.5, client=client)

    assert "403" in str(captured.value)
    assert "secret-service-key" not in str(captured.value)
    assert captured.value.__cause__ is None


def test_matches_live_place_to_db_candidate_by_title_and_coordinate() -> None:
    place_id = uuid.uuid4()
    candidate = Candidate(
        place_id=place_id,
        lat=33.5432,
        lng=126.6695,
        item_type=ScheduleItemType.ATTRACTION,
        environment=None,
        average_stay_minutes=60,
    )
    tour_place = TourPlace(
        content_id="123",
        title="함덕 해수욕장",
        latitude=33.5433,
        longitude=126.6696,
    )

    assert _match_tour_places([candidate], {place_id: "함덕해수욕장"}, [tour_place]) == {place_id}
