"""추천 요청부터 일정 저장까지의 API 통합 테스트."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.v1.endpoints import routes
from app.db.models import Place, Route, RouteRequest
from app.recommend.tmap import RouteLeg
from app.recommend.weights import resolve_weights
from app.services import route_recommendation


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
        "userCriteria": ["proximity"],
    }


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
    assert request.applied_weights == pytest.approx(
        resolve_weights("pet", ["proximity"]).model_dump()
    )


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
    db.expire_all()

    route = db.get(Route, route_id)
    assert route is not None
    assert route.status.value == "generated"
    first_item = route.route_days[0].items[0]
    assert first_item.place_id is not None
    assert db.get(Place, first_item.place_id) is not None
    assert first_item.recommendation_score is not None

    status_response = client.get(f"/api/v1/routes/{route_id}/status")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "generated"
