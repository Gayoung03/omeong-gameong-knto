"""추천 요청부터 일정 저장까지의 API 통합 테스트."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.v1.endpoints import routes
from app.db.models import Place, Route, RouteRequest
from app.integrations.tour_api.kto import TourPlace
from app.recommend.tmap import RouteLeg
from app.recommend.weights import resolve_weights
from app.services import route_recommendation


@pytest.fixture(autouse=True)
def _no_external_tour_api(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(route_recommendation, "_tour_api_places", lambda *_args: [])
    monkeypatch.setattr(routes, "get_nearby_places", lambda *_args, **_kwargs: [])


def _payload(place_id: uuid.UUID) -> dict:
    return {
        "title": "몽이랑 제주",
        "startAt": "2026-09-10T09:00:00+09:00",
        "endAt": "2026-09-10T18:00:00+09:00",
        "departurePlaceId": str(place_id),
        "pace": "relaxed",
        "transport": "rental_car",
        "preferredTags": ["바다"],
        "priorityPreset": "pet",
        "userCriteria": [],
    }


def _seed_dinner_restaurant(db: Session, *, lat: float = 33.395, lng: float = 126.240) -> Place:
    """엔진은 매일 마지막 슬롯을 반려동물 동반 저녁 식당으로 채운다
    (route_recommendation.py: "모든 날짜에 배치할 수 있는 반려동물 동반 저녁
    식당" 규칙). 그 후보가 하나도 없으면 생성이 실패한다.

    동반정책 행은 넣지 않는다 — `is_pet_compatible` 이 정책 없음을 통과 처리하므로
    (filters.py:41), 정책 없음 경로가 그대로 검증에 남는다(#133 합의).
    """
    restaurant = Place(
        id=uuid.uuid4(),
        name="동반 가능 저녁 식당",
        category="restaurant",
        latitude=lat,
        longitude=lng,
        average_stay_minutes=60,
    )
    db.add(restaurant)
    db.flush()
    return restaurant


def test_route_request_saves_resolved_weight_snapshot(
    client: TestClient,
    db: Session,
    place: Place,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generated: list[uuid.UUID] = []
    monkeypatch.setattr(
        routes,
        "run_route_generation",
        lambda route_id, _open: generated.append(route_id),
    )

    response = client.post("/api/v1/route-requests", json=_payload(place.id))

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "generating"
    assert generated == [uuid.UUID(body["routeId"])]

    request = db.get(RouteRequest, uuid.UUID(body["routeRequestId"]))
    assert request is not None
    assert request.applied_weights == pytest.approx(resolve_weights("pet", []).model_dump())


def test_route_request_rejects_transport_without_route_provider(
    client: TestClient,
    place: Place,
) -> None:
    payload = _payload(place.id)
    payload["transport"] = "public_transport"

    response = client.post("/api/v1/route-requests", json=payload)

    assert response.status_code == 422
    assert "지원하지 않는 이동수단" in response.json()["detail"]


def test_route_request_generates_db_place_itinerary(
    client: TestClient,
    db: Session,
    place: Place,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    accommodation = Place(
        id=uuid.uuid4(),
        name="추천에서 제외할 숙소",
        category="accommodation",
        latitude=33.41,
        longitude=126.26,
    )
    db.add(accommodation)
    db.flush()
    _seed_dinner_restaurant(db)
    monkeypatch.setattr(routes, "run_route_generation", lambda _route_id, _open: None)
    created = client.post("/api/v1/route-requests", json=_payload(place.id)).json()
    route_id = uuid.UUID(created["routeId"])
    monkeypatch.setattr(
        route_recommendation,
        "get_route",
        lambda *_args, **_kwargs: RouteLeg(distance_m=0, duration_min=0, polyline=None),
    )
    monkeypatch.setattr(
        route_recommendation,
        "get_precipitation_probabilities",
        lambda *_args, **_kwargs: {},
    )
    monkeypatch.setattr(
        route_recommendation,
        "_tour_api_places",
        lambda *_args: [
            TourPlace(
                content_id="tour-1",
                title=place.name,
                latitude=float(place.latitude),
                longitude=float(place.longitude),
            )
        ],
    )

    route_recommendation.generate_route(db, route_id)
    db.expire_all()

    route = db.get(Route, route_id)
    assert route is not None
    assert route.status.value == "generated"
    recommended_items = [
        item
        for day in route.route_days
        for item in day.items
        if item.recommendation_score is not None
    ]
    assert recommended_items
    assert recommended_items[0].place_id is not None
    assert db.get(Place, recommended_items[0].place_id) is not None
    assert all(item.place_id != accommodation.id for day in route.route_days for item in day.items)
    assert "한국관광공사 TourAPI 실시간 관광정보 1건" in (route.explanation or "")

    status_response = client.get(f"/api/v1/routes/{route_id}/status")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "generated"


def test_user_can_confirm_replacement_and_refresh_adjacent_routes(
    client: TestClient,
    db: Session,
    place: Place,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    second = Place(
        id=uuid.uuid4(),
        name="기존 카페",
        category="cafe",
        latitude=33.40,
        longitude=126.25,
        average_stay_minutes=60,
    )
    db.add(second)
    db.flush()
    _seed_dinner_restaurant(db)
    monkeypatch.setattr(routes, "run_route_generation", lambda _route_id, _open: None)
    created = client.post("/api/v1/route-requests", json=_payload(place.id)).json()
    route_id = uuid.UUID(created["routeId"])
    route_calls: list[tuple] = []

    def fake_route(*args, **_kwargs) -> RouteLeg:
        route_calls.append(args)
        return RouteLeg(distance_m=1000, duration_min=5, polyline=None)

    monkeypatch.setattr(route_recommendation, "get_route", fake_route)
    monkeypatch.setattr(
        route_recommendation,
        "get_precipitation_probabilities",
        lambda *_args, **_kwargs: {},
    )
    route_recommendation.generate_route(db, route_id)

    route = db.get(Route, route_id)
    assert route is not None
    items = [
        item
        for day in route.route_days
        for item in day.items
        if item.recommendation_score is not None
    ]
    assert len(items) >= 2

    duplicate = client.put(
        f"/api/v1/route-items/{items[0].id}/place",
        json={"placeId": str(items[1].place_id)},
    )
    assert duplicate.status_code == 422

    replacement = Place(
        id=uuid.uuid4(),
        name="새 산책 장소",
        category="attraction",
        latitude=33.41,
        longitude=126.26,
        average_stay_minutes=90,
    )
    db.add(replacement)
    db.flush()
    route_calls.clear()

    response = client.put(
        f"/api/v1/route-items/{items[0].id}/place",
        json={"placeId": str(replacement.id)},
    )

    assert response.status_code == 200
    assert response.json()["place"]["id"] == str(replacement.id)
    assert response.json()["customPlaceName"] is None
    assert response.json()["latitude"] == pytest.approx(float(replacement.latitude))
    assert response.json()["longitude"] == pytest.approx(float(replacement.longitude))
    assert route_calls
    db.refresh(route)
    assert route.version == 2
    assert route.total_score is not None


def test_replacement_rejects_place_that_fails_hard_filter(
    client: TestClient,
    db: Session,
    place: Place,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # 생성이 성공해야 교체 대상 항목이 생긴다. 저녁 식당 후보를 하나 심어
    # 초기 일정 생성을 통과시킨다. 이 식당은 활성·정책 없음이라, 뒤에서 비활성
    # 장소로 교체 시도가 하드 필터에 걸려 거부되는 검증 대상과는 무관하다.
    _seed_dinner_restaurant(db)
    monkeypatch.setattr(routes, "run_route_generation", lambda _route_id, _open: None)
    created = client.post("/api/v1/route-requests", json=_payload(place.id)).json()
    route_id = uuid.UUID(created["routeId"])
    monkeypatch.setattr(
        route_recommendation,
        "get_route",
        lambda *_args, **_kwargs: RouteLeg(distance_m=0, duration_min=0, polyline=None),
    )
    monkeypatch.setattr(
        route_recommendation,
        "get_precipitation_probabilities",
        lambda *_args, **_kwargs: {},
    )
    route_recommendation.generate_route(db, route_id)
    route = db.get(Route, route_id)
    assert route is not None
    item = next(
        item
        for day in route.route_days
        for item in day.items
        if item.recommendation_score is not None
    )
    original_place_id = item.place_id

    inactive = Place(
        id=uuid.uuid4(),
        name="운영 중단 장소",
        category="cafe",
        latitude=33.42,
        longitude=126.27,
        is_active=False,
    )
    db.add(inactive)
    db.flush()

    response = client.put(
        f"/api/v1/route-items/{item.id}/place",
        json={"placeId": str(inactive.id)},
    )

    assert response.status_code == 422
    db.refresh(item)
    assert item.place_id == original_place_id
