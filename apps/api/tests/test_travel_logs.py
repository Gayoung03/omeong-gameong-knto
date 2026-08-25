"""여행기록 테스트.

여기서 지키려는 것은 네 가지다 — **남의 기록이 열리지 않을 것**,
필터가 실제로 좁힐 것, **한 날짜에 대표가 하나만 남을 것**, 그리고
**이름·사진이 스냅샷으로 박제될 것**.

대표는 DB 제약이 없어서 서버가 지키지 않으면 아무도 안 지킨다.
스냅샷은 원본 프로필을 바꾼 뒤 기록이 따라 바뀌는지로 확인한다.
"""

import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.v1.endpoints import travel_logs as travel_logs_endpoint
from app.db.models import Notification, Pet, Place, Route, TravelLog, TravelLogPet, User
from app.db.models.enums import (
    PetSpecies,
    RouteCreationType,
    RouteStatus,
    TransportType,
    TripPace,
)
from app.integrations.llm.travel_log_image import ImageGenerationError

KST = timezone(timedelta(hours=9))


def _make_log(
    db: Session,
    user: User,
    *,
    recorded_date: date,
    route: Route | None = None,
    place: Place | None = None,
    place_name: str = "함덕해수욕장",
    is_representative: bool = False,
    pets: list[Pet] | None = None,
) -> TravelLog:
    log = TravelLog(
        id=uuid.uuid4(),
        user_id=user.id,
        route_id=route.id if route else None,
        place_id=place.id if place else None,
        place_name_snapshot=place_name,
        recorded_date=recorded_date,
        visited_at=datetime.combine(recorded_date, datetime.min.time(), tzinfo=KST),
        original_image_url="https://example.test/original.jpg",
        generated_image_url="https://example.test/generated.jpg",
        writing_style="dog_diary",
        mood="happy",
        generation_status="completed",
        is_representative=is_representative,
    )
    db.add(log)
    db.flush()

    for pet in pets or []:
        db.add(
            TravelLogPet(
                id=uuid.uuid4(),
                travel_log_id=log.id,
                pet_id=pet.id,
                pet_name_snapshot=pet.name,
                pet_profile_image_snapshot=pet.image_url,
            )
        )
    db.flush()
    return log


@pytest.fixture
def pet(db: Session, owner: User) -> Pet:
    pet = Pet(
        id=uuid.uuid4(),
        user_id=owner.id,
        name="몽이",
        species=PetSpecies.DOG,
        image_url="https://example.test/mong.jpg",
    )
    db.add(pet)
    db.flush()
    return pet


@pytest.fixture
def log(db: Session, owner: User, place: Place) -> TravelLog:
    return _make_log(db, owner, recorded_date=date(2026, 9, 10), place=place)


# ---------------------------------------------------------------------------
# 목록과 필터
# ---------------------------------------------------------------------------


def test_내_기록만_보인다(client: TestClient, db: Session, owner: User, stranger: User) -> None:
    _make_log(db, owner, recorded_date=date(2026, 9, 10))
    _make_log(db, stranger, recorded_date=date(2026, 9, 11))

    body = client.get("/api/v1/travel-logs").json()

    assert body["total"] == 1


def test_최신순으로_내려온다(client: TestClient, db: Session, owner: User) -> None:
    _make_log(db, owner, recorded_date=date(2026, 9, 10), place_name="먼저")
    _make_log(db, owner, recorded_date=date(2026, 9, 12), place_name="나중")

    items = client.get("/api/v1/travel-logs").json()["items"]

    assert [item["placeNameSnapshot"] for item in items] == ["나중", "먼저"]


def test_routeId_none_은_개별_기록만_준다(
    client: TestClient, db: Session, owner: User, trip: Route
) -> None:
    _make_log(db, owner, recorded_date=date(2026, 9, 11), route=trip)
    _make_log(db, owner, recorded_date=date(2026, 9, 12), place_name="개별")

    body = client.get("/api/v1/travel-logs", params={"routeId": "none"}).json()

    assert body["total"] == 1
    assert body["items"][0]["placeNameSnapshot"] == "개별"


def test_routeId_로_그_여행의_기록만_준다(
    client: TestClient, db: Session, owner: User, trip: Route
) -> None:
    _make_log(db, owner, recorded_date=date(2026, 9, 11), route=trip)
    _make_log(db, owner, recorded_date=date(2026, 9, 12))

    body = client.get("/api/v1/travel-logs", params={"routeId": str(trip.id)}).json()

    assert body["total"] == 1
    assert body["items"][0]["routeId"] == str(trip.id)


def test_routeId_가_UUID_도_none_도_아니면_422(client: TestClient) -> None:
    response = client.get("/api/v1/travel-logs", params={"routeId": "아무거나"})

    assert response.status_code == 422


def test_petIds_로_거른다(client: TestClient, db: Session, owner: User, pet: Pet) -> None:
    _make_log(db, owner, recorded_date=date(2026, 9, 10), pets=[pet])
    _make_log(db, owner, recorded_date=date(2026, 9, 11))

    body = client.get("/api/v1/travel-logs", params={"petIds": str(pet.id)}).json()

    assert body["total"] == 1
    assert body["items"][0]["companions"][0]["nameSnapshot"] == "몽이"


def test_반려동물_두_마리가_함께_있어도_한_줄로_센다(
    client: TestClient, db: Session, owner: User, pet: Pet
) -> None:
    """조인으로 걸렀다면 여기서 total 이 2 가 되어 페이지가 어긋난다."""
    second = Pet(id=uuid.uuid4(), user_id=owner.id, name="가멍", species=PetSpecies.CAT)
    db.add(second)
    db.flush()
    _make_log(db, owner, recorded_date=date(2026, 9, 10), pets=[pet, second])

    body = client.get(
        "/api/v1/travel-logs", params={"petIds": [str(pet.id), str(second.id)]}
    ).json()

    assert body["total"] == 1
    assert len(body["items"]) == 1


def test_placeQuery_로_장소명을_검색한다(client: TestClient, db: Session, owner: User) -> None:
    _make_log(db, owner, recorded_date=date(2026, 9, 10), place_name="함덕해수욕장")
    _make_log(db, owner, recorded_date=date(2026, 9, 11), place_name="애월 카페")

    body = client.get("/api/v1/travel-logs", params={"placeQuery": "함덕"}).json()

    assert body["total"] == 1


def test_from_과_to_로_날짜를_자른다(client: TestClient, db: Session, owner: User) -> None:
    for day in (5, 10, 15):
        _make_log(db, owner, recorded_date=date(2026, 9, day))

    body = client.get(
        "/api/v1/travel-logs", params={"from": "2026-09-08", "to": "2026-09-12"}
    ).json()

    assert body["total"] == 1
    assert body["items"][0]["recordedDate"] == "2026-09-10"


# ---------------------------------------------------------------------------
# 소유권 — 없으면 404, 남의 것이면 403
# ---------------------------------------------------------------------------


def test_없는_기록은_404(client: TestClient) -> None:
    response = client.get(f"/api/v1/travel-logs/{uuid.uuid4()}")

    assert response.status_code == 404


def test_남의_기록은_403(client: TestClient, db: Session, stranger: User) -> None:
    other = _make_log(db, stranger, recorded_date=date(2026, 9, 10))

    assert client.get(f"/api/v1/travel-logs/{other.id}").status_code == 403
    assert (
        client.patch(
            f"/api/v1/travel-logs/{other.id}", json={"personalMessage": "가로채기"}
        ).status_code
        == 403
    )
    assert client.delete(f"/api/v1/travel-logs/{other.id}").status_code == 403


# ---------------------------------------------------------------------------
# 수정
# ---------------------------------------------------------------------------


def test_보낸_필드만_바뀐다(client: TestClient, log: TravelLog) -> None:
    body = client.patch(
        f"/api/v1/travel-logs/{log.id}", json={"personalMessage": "몽이가 처음 본 바다"}
    ).json()

    assert body["personalMessage"] == "몽이가 처음 본 바다"
    assert body["placeNameSnapshot"] == "함덕해수욕장"
    assert body["writingStyle"] == "dog_diary"


def test_미래_날짜로는_못_바꾼다(client: TestClient, log: TravelLog) -> None:
    tomorrow = datetime.now(KST).date() + timedelta(days=1)

    response = client.patch(
        f"/api/v1/travel-logs/{log.id}", json={"recordedDate": tomorrow.isoformat()}
    )

    assert response.status_code == 422


def test_대표로_지정하면_같은_날짜의_기존_대표가_내려간다(
    client: TestClient, db: Session, owner: User
) -> None:
    old = _make_log(db, owner, recorded_date=date(2026, 9, 10), is_representative=True)
    new = _make_log(db, owner, recorded_date=date(2026, 9, 10))

    body = client.patch(f"/api/v1/travel-logs/{new.id}", json={"isRepresentative": True}).json()

    assert body["isRepresentative"] is True
    db.refresh(old)
    assert old.is_representative is False


def test_다른_날짜의_대표는_건드리지_않는다(client: TestClient, db: Session, owner: User) -> None:
    other_day = _make_log(db, owner, recorded_date=date(2026, 9, 9), is_representative=True)
    target = _make_log(db, owner, recorded_date=date(2026, 9, 10))

    client.patch(f"/api/v1/travel-logs/{target.id}", json={"isRepresentative": True})

    db.refresh(other_day)
    assert other_day.is_representative is True


def test_petIds_를_보내면_스냅샷이_갱신된다(
    client: TestClient, db: Session, owner: User, pet: Pet, log: TravelLog
) -> None:
    """프로필 이름을 바꾼 뒤 다시 저장하면 새 이름이 박제된다."""
    pet.name = "이름바꾼몽이"
    db.flush()

    body = client.patch(f"/api/v1/travel-logs/{log.id}", json={"petIds": [str(pet.id)]}).json()

    assert [c["nameSnapshot"] for c in body["companions"]] == ["이름바꾼몽이"]


def test_petIds_를_빈_배열로_보내면_전부_지워진다(
    client: TestClient, db: Session, owner: User, pet: Pet
) -> None:
    log = _make_log(db, owner, recorded_date=date(2026, 9, 10), pets=[pet])

    body = client.patch(f"/api/v1/travel-logs/{log.id}", json={"petIds": []}).json()

    assert body["companions"] == []


def test_남의_반려동물은_붙일_수_없다(
    client: TestClient, db: Session, stranger: User, log: TravelLog
) -> None:
    others = Pet(id=uuid.uuid4(), user_id=stranger.id, name="남의개", species=PetSpecies.DOG)
    db.add(others)
    db.flush()

    response = client.patch(f"/api/v1/travel-logs/{log.id}", json={"petIds": [str(others.id)]})

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# 삭제
# ---------------------------------------------------------------------------


def test_삭제하면_반려동물_행도_함께_사라진다(
    client: TestClient, db: Session, owner: User, pet: Pet
) -> None:
    log = _make_log(db, owner, recorded_date=date(2026, 9, 10), pets=[pet])
    log_id = log.id

    response = client.delete(f"/api/v1/travel-logs/{log_id}")

    assert response.status_code == 204
    assert db.get(TravelLog, log_id) is None
    assert db.query(TravelLogPet).filter(TravelLogPet.travel_log_id == log_id).count() == 0


# ---------------------------------------------------------------------------
# 그룹
# ---------------------------------------------------------------------------


def test_여행_기록과_개별_기록이_각각_묶인다(
    client: TestClient, db: Session, owner: User, trip: Route
) -> None:
    _make_log(db, owner, recorded_date=date(2026, 9, 11), route=trip)
    _make_log(db, owner, recorded_date=date(2026, 9, 12), route=trip)
    _make_log(db, owner, recorded_date=date(2026, 8, 3))

    body = client.get("/api/v1/travel-logs/groups").json()

    assert body["total"] == 2
    kinds = [item["kind"] for item in body["items"]]
    # 여행 기록(9월)이 개별 기록(8월)보다 최신이라 앞에 온다.
    assert kinds == ["route", "ungrouped"]

    route_group = body["items"][0]["route"]
    assert route_group["id"] == str(trip.id)
    assert route_group["logCount"] == 2
    assert len(route_group["previewLogs"]) == 2

    month_group = body["items"][1]["group"]
    assert (month_group["year"], month_group["month"]) == (2026, 8)
    assert month_group["logCount"] == 1


def test_같은_달의_개별_기록은_한_그룹이다(client: TestClient, db: Session, owner: User) -> None:
    _make_log(db, owner, recorded_date=date(2026, 8, 3))
    _make_log(db, owner, recorded_date=date(2026, 8, 20))

    body = client.get("/api/v1/travel-logs/groups").json()

    assert body["total"] == 1
    assert body["items"][0]["group"]["logCount"] == 2


def test_미리보기는_최대_네_건이다(client: TestClient, db: Session, owner: User) -> None:
    for day in range(1, 7):
        _make_log(db, owner, recorded_date=date(2026, 8, day))

    group = client.get("/api/v1/travel-logs/groups").json()["items"][0]["group"]

    assert group["logCount"] == 6
    assert len(group["previewLogs"]) == 4
    # 최신순으로 앞의 네 건이다.
    assert [item["recordedDate"] for item in group["previewLogs"]] == [
        "2026-08-06",
        "2026-08-05",
        "2026-08-04",
        "2026-08-03",
    ]


def test_그룹에_여행의_반려동물이_담긴다(
    client: TestClient, db: Session, owner: User, trip: Route, pet: Pet
) -> None:
    """기록의 companions 가 아니라 **여행 자체**의 반려동물이다."""
    from app.db.models import RoutePet

    db.add(RoutePet(route_id=trip.id, pet_id=pet.id))
    db.flush()
    _make_log(db, owner, recorded_date=date(2026, 9, 11), route=trip)

    group = client.get("/api/v1/travel-logs/groups").json()["items"][0]["route"]

    assert [c["nameSnapshot"] for c in group["companions"]] == ["몽이"]


def test_남의_기록은_그룹에도_없다(client: TestClient, db: Session, stranger: User) -> None:
    _make_log(db, stranger, recorded_date=date(2026, 9, 10))

    body = client.get("/api/v1/travel-logs/groups").json()

    assert body["total"] == 0
    assert body["items"] == []


# ---------------------------------------------------------------------------
# 생성 — "접수했습니다" 방식
# ---------------------------------------------------------------------------


def _create_body(**overrides: object) -> dict:
    body = {
        "recordedDate": "2026-08-11",
        "originalImageUrl": "https://example.test/upload.jpg",
        "writingStyle": "dog_diary",
        "placeName": "함덕해수욕장",
    }
    body.update(overrides)
    return body


def test_생성하면_202_와_생성중_상태를_준다(client: TestClient) -> None:
    response = client.post("/api/v1/travel-logs", json=_create_body())

    assert response.status_code == 202
    assert response.json()["generationStatus"] == "generating"


def test_생성이_끝나면_completed_가_되고_목록에_뜬다(client: TestClient) -> None:
    """TestClient 는 응답을 돌려준 뒤 뒷작업을 **동기로** 돌린다.

    그래서 실제 서비스처럼 기다리지 않아도 다음 요청에서 결과를 볼 수 있다.
    """
    created = client.post("/api/v1/travel-logs", json=_create_body()).json()

    status_body = client.get(f"/api/v1/travel-logs/{created['id']}/status").json()

    assert status_body["generationStatus"] == "completed"
    # 임시 생성기라 원본이 그대로 결과물이 된다.
    assert status_body["generatedImageUrl"] == "https://example.test/upload.jpg"
    assert client.get("/api/v1/travel-logs").json()["total"] == 1


def test_장소를_id_로_보내면_그때_이름이_박제된다(
    client: TestClient, db: Session, place: Place
) -> None:
    created = client.post(
        "/api/v1/travel-logs", json=_create_body(placeId=str(place.id), placeName=None)
    ).json()

    # 장소 이름이 나중에 바뀌어도 기록은 따라 바뀌지 않는다.
    place.name = "이름이 바뀐 해변"
    db.flush()

    body = client.get(f"/api/v1/travel-logs/{created['id']}").json()

    assert body["placeNameSnapshot"] == "테스트 해변"


def test_반려동물도_스냅샷으로_복사된다(
    client: TestClient, db: Session, pet: Pet
) -> None:
    created = client.post(
        "/api/v1/travel-logs", json=_create_body(petIds=[str(pet.id)])
    ).json()

    pet.name = "이름이 바뀐 몽이"
    db.flush()

    body = client.get(f"/api/v1/travel-logs/{created['id']}").json()

    assert [c["nameSnapshot"] for c in body["companions"]] == ["몽이"]


def test_장소를_아무것도_안_보내면_422(client: TestClient) -> None:
    response = client.post("/api/v1/travel-logs", json=_create_body(placeName=None))

    assert response.status_code == 422


def test_미래_날짜로는_못_만든다(client: TestClient) -> None:
    tomorrow = datetime.now(KST).date() + timedelta(days=1)

    response = client.post(
        "/api/v1/travel-logs", json=_create_body(recordedDate=tomorrow.isoformat())
    )

    assert response.status_code == 422


def test_남의_여행에는_못_붙인다(
    client: TestClient, db: Session, stranger: User
) -> None:
    others_route = Route(
        id=uuid.uuid4(),
        user_id=stranger.id,
        title="남의 여행",
        status=RouteStatus.GENERATED,
        creation_type=RouteCreationType.MANUAL,
        start_at=datetime(2026, 9, 11, 9, 0, tzinfo=KST),
        end_at=datetime(2026, 9, 12, 9, 0, tzinfo=KST),
        pace=TripPace.NORMAL,
        transport=TransportType.RENTAL_CAR,
    )
    db.add(others_route)
    db.flush()

    response = client.post(
        "/api/v1/travel-logs", json=_create_body(routeId=str(others_route.id))
    )

    assert response.status_code == 403


def test_남의_반려동물은_못_붙인다(
    client: TestClient, db: Session, stranger: User
) -> None:
    others = Pet(id=uuid.uuid4(), user_id=stranger.id, name="남의개", species=PetSpecies.DOG)
    db.add(others)
    db.flush()

    response = client.post(
        "/api/v1/travel-logs", json=_create_body(petIds=[str(others.id)])
    )

    assert response.status_code == 403


def test_완성되면_알림이_쌓인다(client: TestClient, db: Session, owner: User) -> None:
    client.post("/api/v1/travel-logs", json=_create_body())

    notification = db.scalars(
        select(Notification).where(Notification.user_id == owner.id)
    ).one()

    assert notification.type == "travel_log_ready"
    assert "함덕해수욕장" in notification.content


# ---------------------------------------------------------------------------
# 생성 실패와 재생성
# ---------------------------------------------------------------------------


def test_그림을_못_만들면_failed_로_남고_알림은_없다(
    client: TestClient, db: Session, owner: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    """행을 지우지 않는 것이 핵심이다 — 지우면 다시 만들 대상이 사라진다."""

    def boom(*args: object, **kwargs: object) -> str:
        raise ImageGenerationError("생성기 고장")

    monkeypatch.setattr(travel_logs_endpoint, "generate_log_image", boom)

    created = client.post("/api/v1/travel-logs", json=_create_body()).json()

    body = client.get(f"/api/v1/travel-logs/{created['id']}/status").json()
    assert body["generationStatus"] == "failed"
    assert body["generatedImageUrl"] is None
    assert (
        db.scalar(select(func.count()).select_from(Notification).where(
            Notification.user_id == owner.id
        ))
        == 0
    )


def test_재생성하면_실패한_기록도_되살아난다(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*args: object, **kwargs: object) -> str:
        raise ImageGenerationError("생성기 고장")

    monkeypatch.setattr(travel_logs_endpoint, "generate_log_image", boom)
    created = client.post("/api/v1/travel-logs", json=_create_body()).json()
    monkeypatch.undo()

    response = client.post(f"/api/v1/travel-logs/{created['id']}/regenerate", json={})

    assert response.status_code == 202
    body = client.get(f"/api/v1/travel-logs/{created['id']}/status").json()
    assert body["generationStatus"] == "completed"


def test_재생성으로_말투를_바꿀_수_있다(client: TestClient) -> None:
    created = client.post("/api/v1/travel-logs", json=_create_body()).json()

    client.post(
        f"/api/v1/travel-logs/{created['id']}/regenerate",
        json={"writingStyle": "jeju_dialect", "mood": "excited"},
    )

    body = client.get(f"/api/v1/travel-logs/{created['id']}").json()
    assert body["writingStyle"] == "jeju_dialect"
    assert body["mood"] == "excited"
    # 원본 사진은 그대로 둔다.
    assert body["originalImageUrl"] == "https://example.test/upload.jpg"


def test_남의_기록은_상태도_재생성도_막힌다(
    client: TestClient, db: Session, stranger: User
) -> None:
    other = _make_log(db, stranger, recorded_date=date(2026, 9, 10))

    assert client.get(f"/api/v1/travel-logs/{other.id}/status").status_code == 403
    assert (
        client.post(f"/api/v1/travel-logs/{other.id}/regenerate", json={}).status_code
        == 403
    )
