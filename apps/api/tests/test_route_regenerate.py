"""POST /routes/{routeId}/regenerate (routes.md L729-760).

기존 결과를 지우지 않고 같은 route_request 로 새 version 을 만든다. 실제 생성은
백그라운드라 대부분 no-op 으로 막고, 새 Route 행과 상태·경쟁 처리만 본다.
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.endpoints import routes
from app.db.models import (
    Pet,
    Place,
    PlacePetPolicy,
    Route,
    RoutePet,
    RouteRequest,
    RouteRequestPet,
    User,
)
from app.db.models.enums import (
    DataProvider,
    PetPolicyType,
    PetSpecies,
    RouteCreationType,
    RouteStatus,
    TransportType,
    TripPace,
)
from app.recommend.weights import resolve_weights
from app.services import route_recommendation as rr
from app.services.route_recommendation import generate_route

KST = timezone(timedelta(hours=9))


def _recommended_route(
    db: Session,
    user: User,
    *,
    applied_weights: dict | None = None,
    version: int = 1,
) -> tuple[Route, RouteRequest]:
    start = datetime(2026, 9, 20, 9, tzinfo=KST)
    request = RouteRequest(
        id=uuid.uuid4(),
        user_id=user.id,
        start_at=start,
        end_at=start + timedelta(hours=10),
        pace=TripPace.NORMAL,
        transport=TransportType.RENTAL_CAR,
        companion_count=1,
        departure_latitude=Decimal("33.4900000"),
        departure_longitude=Decimal("126.5300000"),
        applied_weights=applied_weights,
    )
    db.add(request)
    db.flush()
    route = Route(
        id=uuid.uuid4(),
        route_request_id=request.id,
        user_id=user.id,
        title="추천 여행",
        status=RouteStatus.GENERATED,
        creation_type=RouteCreationType.RECOMMENDED,
        version=version,
        start_at=request.start_at,
        end_at=request.end_at,
        pace=TripPace.NORMAL,
        transport=TransportType.RENTAL_CAR,
    )
    db.add(route)
    db.flush()
    return route, request


def _add_version(db: Session, user: User, request: RouteRequest, *, version: int) -> Route:
    """같은 route_request 아래 다른 version 의 Route 를 하나 더 넣는다(경쟁 상황 재현)."""
    route = Route(
        id=uuid.uuid4(),
        route_request_id=request.id,
        user_id=user.id,
        title="다른 version",
        status=RouteStatus.GENERATED,
        creation_type=RouteCreationType.RECOMMENDED,
        version=version,
        start_at=request.start_at,
        end_at=request.end_at,
        pace=TripPace.NORMAL,
        transport=TransportType.RENTAL_CAR,
    )
    db.add(route)
    db.flush()
    return route


def test_regenerate_creates_new_version_and_copies_pets(
    client: TestClient, db: Session, owner: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(routes, "run_route_generation", lambda _route_id, _open: None)
    route, request = _recommended_route(db, owner)
    pet = Pet(id=uuid.uuid4(), user_id=owner.id, name="몽이", species=PetSpecies.DOG)
    db.add(pet)
    db.flush()
    db.add(RouteRequestPet(route_request_id=request.id, pet_id=pet.id))
    db.flush()

    response = client.post(f"/api/v1/routes/{route.id}/regenerate")

    assert response.status_code == 202
    body = response.json()
    assert body["version"] == 2
    assert body["status"] == "generating"
    assert body["routeRequestId"] == str(request.id)
    assert body["routeId"] != str(route.id)

    new_route = db.get(Route, uuid.UUID(body["routeId"]))
    assert new_route is not None
    assert new_route.creation_type == RouteCreationType.RECOMMENDED
    assert new_route.route_request_id == request.id
    # 원본은 그대로 남는다.
    assert db.get(Route, route.id) is not None
    # route_pets 가 새 version 에도 붙는다(기존 생성 경로와 동일).
    copied = db.scalars(select(RoutePet.pet_id).where(RoutePet.route_id == new_route.id)).all()
    assert list(copied) == [pet.id]


def test_regenerate_other_users_route_is_403(
    client: TestClient, db: Session, stranger: User
) -> None:
    route, _ = _recommended_route(db, stranger)

    response = client.post(f"/api/v1/routes/{route.id}/regenerate")

    assert response.status_code == 403


def test_regenerate_missing_route_is_404(client: TestClient) -> None:
    response = client.post(f"/api/v1/routes/{uuid.uuid4()}/regenerate")

    assert response.status_code == 404


def test_regenerate_manual_route_is_422(client: TestClient, trip: Route) -> None:
    # trip 픽스처는 manual(route_request_id NULL) 여행이다.
    response = client.post(f"/api/v1/routes/{trip.id}/regenerate")

    assert response.status_code == 422
    assert response.json()["detail"] == "직접 만든 여행은 다시 추천받을 수 없어요"


def test_regenerate_unique_conflict_retries_once(
    client: TestClient, db: Session, owner: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    """첫 시도가 UNIQUE(route_request_id, version) 충돌이면 max+1 로 1회 재시도한다."""
    monkeypatch.setattr(routes, "run_route_generation", lambda _route_id, _open: None)
    route, request = _recommended_route(db, owner)
    _add_version(db, owner, request, version=2)  # 이미 version 2 존재 → version 2 시도는 충돌

    real_next = routes._next_version
    calls: list[int] = []

    def fake_next(session: Session, route_request_id: uuid.UUID) -> int:
        calls.append(1)
        return 2 if len(calls) == 1 else real_next(session, route_request_id)

    monkeypatch.setattr(routes, "_next_version", fake_next)

    response = client.post(f"/api/v1/routes/{route.id}/regenerate")

    assert response.status_code == 202
    assert response.json()["version"] == 3  # 2 는 충돌 → max(2)+1
    assert len(calls) == 2


def test_regenerate_unique_conflict_gives_up_with_409(
    client: TestClient, db: Session, owner: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    route, request = _recommended_route(db, owner)
    _add_version(db, owner, request, version=2)

    # 재시도해도 계속 충돌 version(2)만 고르면 409.
    monkeypatch.setattr(routes, "_next_version", lambda _s, _rid: 2)

    response = client.post(f"/api/v1/routes/{route.id}/regenerate")

    assert response.status_code == 409


def test_regenerate_non_unique_integrity_error_is_not_409(
    client: TestClient, db: Session, owner: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    """version 경쟁(23505)이 아닌 무결성 오류는 재시도·409 없이 전역 핸들러(500)로 간다."""
    route, _ = _recommended_route(db, owner)
    # version 0 은 CHECK(version_positive, sqlstate 23514) 위반 → 23505 아님.
    monkeypatch.setattr(routes, "_next_version", lambda _s, _rid: 0)

    response = client.post(f"/api/v1/routes/{route.id}/regenerate")

    assert response.status_code == 500
    assert response.status_code != 409


class _StopBuild(Exception):
    """indoor_bias 캡처 후 generate_route 를 조기에 멈추는 신호."""


def _seed_active_attraction(db: Session) -> None:
    place = Place(
        id=uuid.uuid4(),
        name="확실 관광지",
        category="attraction",
        latitude=Decimal("33.4996000"),
        longitude=Decimal("126.5312000"),
        average_stay_minutes=60,
        is_active=True,
    )
    db.add(place)
    db.flush()
    db.add(
        PlacePetPolicy(
            place_id=place.id,
            policy_type=PetPolicyType.INDOOR_ALLOWED,
            source=DataProvider.INTERNAL,
        )
    )
    db.flush()


def test_regenerate_reuses_old_request_weather_signal(
    client: TestClient, db: Session, owner: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    """옛 요청(applied_weights.weather=0.10, healing)을 regenerate 하면 indoor_bias 가 켜진다."""
    monkeypatch.setattr(routes, "run_route_generation", lambda _route_id, _open: None)
    applied = resolve_weights("healing").model_dump()
    assert applied["weather"] > 0
    route, _ = _recommended_route(db, owner, applied_weights=applied)

    body = client.post(f"/api/v1/routes/{route.id}/regenerate").json()
    new_route_id = uuid.UUID(body["routeId"])

    # 재생성된 version 을 실제 생성 경로로 돌려 indoor_bias 를 캡처한다.
    monkeypatch.setattr(rr, "_tour_api_places", lambda *_a, **_k: [])
    monkeypatch.setattr(rr, "get_daily_forecasts", lambda *_a, **_k: {})
    captured: dict[str, bool] = {}

    def fake_build(_scored, request, _get_route):
        captured["indoor_bias"] = request.indoor_bias
        raise _StopBuild

    monkeypatch.setattr(rr, "build", fake_build)
    _seed_active_attraction(db)

    with pytest.raises(_StopBuild):
        generate_route(db, new_route_id)
    assert captured["indoor_bias"] is True
