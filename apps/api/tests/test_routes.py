"""여행 조회·편집 엔드포인트 테스트.

여기서 확인하는 것은 **화면이 못 잡아주는 것들**이다 —
남의 여행이 열리는지, 순번에 구멍이 남는지, 허용되지 않은 상태 전이가 통과하는지.
화면을 눌러보는 것으로는 이 셋을 확인할 수 없다.

DB 가 필요한 테스트는 TEST_DATABASE_URL 이 없으면 통째로 건너뛴다(conftest.py 참고).
파일 아래쪽의 스키마 검증 테스트는 DB 없이도 항상 돈다.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db.models import (
    Pet,
    Place,
    PlacePetPolicy,
    Review,
    Route,
    RouteDay,
    TravelLog,
    User,
)
from app.db.models.enums import DataProvider, PetPolicyType, PetSpecies, RouteStatus
from app.schemas.route import RouteItemCreate


def _day_of(trip: Route) -> RouteDay:
    return trip.route_days[0]


def _item_ids_in_order(client: TestClient, trip: Route) -> list[str]:
    response = client.get(f"/api/v1/routes/{trip.id}")
    assert response.status_code == 200
    items = response.json()["routeDays"][0]["items"]
    assert [item["sortOrder"] for item in items] == list(range(len(items)))
    return [item["id"] for item in items]


# ---------------------------------------------------------------------------
# 소유권
# ---------------------------------------------------------------------------


def test_남의_여행은_403(client: TestClient, db: Session, trip: Route, stranger: User) -> None:
    trip.user_id = stranger.id
    db.flush()

    response = client.get(f"/api/v1/routes/{trip.id}")

    # 404 로 뭉뚱그리지 않는다. 명세가 403 과 404 를 나눠뒀다.
    assert response.status_code == 403


def test_없는_여행은_404(client: TestClient) -> None:
    response = client.get(f"/api/v1/routes/{uuid.uuid4()}")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# 일정 편집 — 순번에 구멍이 남지 않는지
# ---------------------------------------------------------------------------


def test_가운데_추가하면_뒤가_밀린다(client: TestClient, trip: Route) -> None:
    before = _item_ids_in_order(client, trip)

    response = client.post(
        f"/api/v1/route-days/{_day_of(trip).id}/items",
        json={"itemType": "cafe", "sortOrder": 1, "customPlaceName": "끼워넣은 카페"},
    )

    assert response.status_code == 201
    assert response.json()["sortOrder"] == 1

    after = _item_ids_in_order(client, trip)
    assert len(after) == len(before) + 1
    assert after[0] == before[0]
    assert after[1] == response.json()["id"]
    assert after[2:] == before[1:]


def test_맨_뒤를_넘는_순번은_맨_뒤로(client: TestClient, trip: Route) -> None:
    response = client.post(
        f"/api/v1/route-days/{_day_of(trip).id}/items",
        json={"itemType": "custom", "sortOrder": 99, "customPlaceName": "마지막"},
    )

    assert response.status_code == 201
    # 99 로 저장하면 순번에 구멍이 생긴다. 목록 끝자리로 눌러 담는다.
    assert response.json()["sortOrder"] == 3


def test_순서_변경은_0부터_다시_매긴다(client: TestClient, trip: Route) -> None:
    original = _item_ids_in_order(client, trip)
    reversed_ids = list(reversed(original))

    response = client.put(
        f"/api/v1/route-days/{_day_of(trip).id}/items/order",
        json={"itemIds": reversed_ids},
    )

    assert response.status_code == 200
    assert [item["sortOrder"] for item in response.json()] == [0, 1, 2]
    assert _item_ids_in_order(client, trip) == reversed_ids


def test_순서를_일부만_보내면_422(client: TestClient, trip: Route) -> None:
    original = _item_ids_in_order(client, trip)

    response = client.put(
        f"/api/v1/route-days/{_day_of(trip).id}/items/order",
        json={"itemIds": original[:2]},
    )

    # 빠진 항목의 순번을 서버가 짐작하지 않는다.
    assert response.status_code == 422


def test_삭제하면_구멍이_남지_않는다(client: TestClient, trip: Route) -> None:
    original = _item_ids_in_order(client, trip)

    response = client.delete(f"/api/v1/route-items/{original[0]}")

    assert response.status_code == 204
    assert _item_ids_in_order(client, trip) == original[1:]


def test_수정은_보낸_필드만_바꾼다(client: TestClient, trip: Route) -> None:
    item_id = _item_ids_in_order(client, trip)[0]
    client.patch(f"/api/v1/route-items/{item_id}", json={"note": "테라스 자리"})

    response = client.patch(f"/api/v1/route-items/{item_id}", json={"stayMinutes": 60})

    assert response.status_code == 200
    assert response.json()["stayMinutes"] == 60
    # note 를 안 보냈으니 지워지면 안 된다.
    assert response.json()["note"] == "테라스 자리"


# ---------------------------------------------------------------------------
# 상태 전이
# ---------------------------------------------------------------------------


def test_허용된_상태_전이는_통과(client: TestClient, trip: Route) -> None:
    response = client.patch(f"/api/v1/routes/{trip.id}", json={"status": "saved"})

    assert response.status_code == 200
    assert response.json()["status"] == "saved"


def test_건너뛰는_상태_전이는_422(client: TestClient, db: Session, trip: Route) -> None:
    trip.status = RouteStatus.SAVED
    db.flush()

    response = client.patch(f"/api/v1/routes/{trip.id}", json={"status": "completed"})

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# 공유
# ---------------------------------------------------------------------------


def test_공유는_토큰을_다시_만들지_않는다(client: TestClient, trip: Route) -> None:
    first = client.post(f"/api/v1/routes/{trip.id}/share").json()
    second = client.post(f"/api/v1/routes/{trip.id}/share").json()

    # 누를 때마다 새로 만들면 예전에 보낸 링크가 조용히 죽는다.
    assert first["shareToken"] == second["shareToken"]
    assert second["isPublic"] is True


def test_공유_화면에는_개인_메모와_토큰이_없다(
    client: TestClient, db: Session, trip: Route
) -> None:
    trip.memo = "선크림 챙기기"
    db.flush()
    token = client.post(f"/api/v1/routes/{trip.id}/share").json()["shareToken"]

    body = client.get(f"/api/v1/routes/shared/{token}").json()

    assert "memo" not in body
    assert "shareToken" not in body
    assert body["title"] == trip.title


def test_공유를_끄면_404(client: TestClient, trip: Route) -> None:
    token = client.post(f"/api/v1/routes/{trip.id}/share").json()["shareToken"]
    client.patch(f"/api/v1/routes/{trip.id}", json={"isPublic": False})

    response = client.get(f"/api/v1/routes/shared/{token}")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# 체크리스트 · 메모
# ---------------------------------------------------------------------------


def test_사용자가_만든_체크리스트는_추천이_아니다(client: TestClient, trip: Route) -> None:
    response = client.post(
        f"/api/v1/routes/{trip.id}/checklist-items",
        json={"category": "pet", "label": "간식", "sortOrder": 5, "isRecommended": True},
    )

    assert response.status_code == 201
    # 앱이 isRecommended 를 보내도 서버가 false 로 고정한다.
    assert response.json()["isRecommended"] is False


def test_메모_수정은_보낸_필드만_바꾼다(client: TestClient, trip: Route) -> None:
    created = client.post(
        f"/api/v1/routes/{trip.id}/memos",
        json={"title": "준비물", "content": "선크림"},
    ).json()

    response = client.patch(f"/api/v1/memos/{created['id']}", json={"content": "선크림, 물그릇"})

    assert response.status_code == 200
    assert response.json()["content"] == "선크림, 물그릇"
    assert response.json()["title"] == "준비물"


def test_남의_여행_날짜에는_메모를_못_단다(
    client: TestClient, db: Session, trip: Route, owner: User
) -> None:
    other = Route(
        id=uuid.uuid4(),
        user_id=owner.id,
        title="다른 여행",
        status=RouteStatus.GENERATED,
        creation_type=trip.creation_type,
        start_at=trip.start_at,
        end_at=trip.end_at,
        pace=trip.pace,
        transport=trip.transport,
    )
    db.add(other)
    db.flush()

    response = client.post(
        f"/api/v1/routes/{other.id}/memos",
        json={"routeDayId": str(_day_of(trip).id), "content": "엉뚱한 곳"},
    )

    # FK 만으로는 "존재하는 날짜"까지만 보장된다. 소속까지 확인해야 한다.
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# 스키마 검증 — DB 없이 항상 돈다
# ---------------------------------------------------------------------------


def test_장소도_이름도_없으면_거절한다() -> None:
    with pytest.raises(ValidationError):
        RouteItemCreate(itemType="custom", sortOrder=0)


def test_끝나는_시각은_시작보다_뒤여야_한다() -> None:
    with pytest.raises(ValidationError):
        RouteItemCreate(
            itemType="cafe",
            sortOrder=0,
            customPlaceName="카페",
            startsAt="2026-09-11T14:00:00+09:00",
            endsAt="2026-09-11T13:00:00+09:00",
        )


def test_직접_입력_일정은_장소_없이도_만들_수_있다() -> None:
    payload = RouteItemCreate(itemType="custom", sortOrder=0, customPlaceName="할머니 댁")

    assert payload.place_id is None
    assert payload.custom_place_name == "할머니 댁"


# ---------------------------------------------------------------------------
# 상세의 계산값 — DB 컬럼이 아니라 세어서 나오는 것들
# ---------------------------------------------------------------------------


def test_일정의_장소에_평점과_동반정책이_붙는다(
    client: TestClient, db: Session, trip: Route, place: Place, stranger: User
) -> None:
    """리뷰·정책 집계가 여행 상세까지 따라오는지.

    노트 03부터 `place` 의 rating·reviewCount·petPolicyType 이 비어 있었다.
    리뷰·장소 API 를 만들면서 집계식이 생겨 이제 채울 수 있다.
    """
    db.add(
        PlacePetPolicy(
            place_id=place.id,
            policy_type=PetPolicyType.OUTDOOR_ONLY,
            source=DataProvider.INTERNAL,
        )
    )
    db.add(Review(id=uuid.uuid4(), user_id=stranger.id, place_id=place.id, rating=4))
    db.flush()

    day_id = trip.route_days[0].id
    client.post(
        f"/api/v1/route-days/{day_id}/items",
        json={"itemType": "attraction", "sortOrder": 0, "placeId": str(place.id)},
    )

    body = client.get(f"/api/v1/routes/{trip.id}").json()
    added = next(item for item in body["routeDays"][0]["items"] if item["place"])

    assert added["place"]["rating"] == 4.0
    assert added["place"]["reviewCount"] == 1
    assert added["place"]["petPolicyType"] == "outdoor_only"


def test_정책이_없는_장소는_상세에서도_unknown(
    client: TestClient, trip: Route, place: Place
) -> None:
    day_id = trip.route_days[0].id
    client.post(
        f"/api/v1/route-days/{day_id}/items",
        json={"itemType": "attraction", "sortOrder": 0, "placeId": str(place.id)},
    )

    body = client.get(f"/api/v1/routes/{trip.id}").json()
    added = next(item for item in body["routeDays"][0]["items"] if item["place"])

    assert added["place"]["petPolicyType"] == "unknown"
    assert added["place"]["rating"] is None
    assert added["place"]["reviewCount"] == 0


def test_여행기록_개수가_목록과_상세에_모두_나온다(
    client: TestClient, db: Session, trip: Route, owner: User
) -> None:
    for _ in range(2):
        db.add(
            TravelLog(
                id=uuid.uuid4(),
                user_id=owner.id,
                route_id=trip.id,
                place_name_snapshot="협재해수욕장",
                recorded_date=trip.start_at.date(),
                original_image_url="https://a",
                writing_style="dog_diary",
            )
        )
    db.flush()

    listed = client.get("/api/v1/routes").json()["items"]
    detail = client.get(f"/api/v1/routes/{trip.id}").json()

    # 여행 모아보기 화면 헤더가 이 값을 쓴다. 목록·상세 양쪽에 있어야 한다.
    assert next(item for item in listed if item["id"] == str(trip.id))["logCount"] == 2
    assert detail["logCount"] == 2


def test_여행기록이_없으면_0(client: TestClient, trip: Route) -> None:
    assert client.get(f"/api/v1/routes/{trip.id}").json()["logCount"] == 0


# ---------------------------------------------------------------------------
# 수동 생성
# ---------------------------------------------------------------------------


def _manual_trip(**overrides: object) -> dict:
    payload = {
        "title": "직접 만든 제주 여행",
        "startAt": "2026-09-11T09:00:00+09:00",
        "endAt": "2026-09-13T18:00:00+09:00",
        "pace": "normal",
        "transport": "rental_car",
    }
    payload.update(overrides)
    return payload


def test_직접_만든_여행은_기간만큼_날짜가_생긴다(client: TestClient) -> None:
    response = client.post("/api/v1/routes", json=_manual_trip())

    assert response.status_code == 201
    body = response.json()

    # 일정 추가가 routeDayId 를 요구하는데 날짜를 만드는 API 가 따로 없다.
    # 기간이 정해지면 날짜도 정해지므로 여기서 함께 만든다.
    assert [day["dayNumber"] for day in body["routeDays"]] == [1, 2, 3]
    assert [day["routeDate"] for day in body["routeDays"]] == [
        "2026-09-11",
        "2026-09-12",
        "2026-09-13",
    ]
    # 껍데기만 만든다. 일정은 편집 API 로 채운다.
    assert all(day["items"] == [] for day in body["routeDays"])


def test_직접_만든_여행은_saved_로_시작한다(client: TestClient) -> None:
    body = client.post("/api/v1/routes", json=_manual_trip()).json()

    # generating 은 "만들어지는 중"이라 수동 여행에 맞지 않는다.
    assert body["status"] == "saved"
    assert body["creationType"] == "manual"
    assert body["version"] == 1


def test_만든_여행에_바로_일정을_넣을_수_있다(client: TestClient) -> None:
    created = client.post("/api/v1/routes", json=_manual_trip()).json()
    day_id = created["routeDays"][0]["id"]

    response = client.post(
        f"/api/v1/route-days/{day_id}/items",
        json={"itemType": "cafe", "sortOrder": 0, "customPlaceName": "첫 일정"},
    )

    assert response.status_code == 201
    assert response.json()["customPlaceName"] == "첫 일정"


def test_끝나는_날이_시작보다_앞서면_422(client: TestClient) -> None:
    response = client.post(
        "/api/v1/routes",
        json=_manual_trip(startAt="2026-09-13T09:00:00+09:00", endAt="2026-09-11T18:00:00+09:00"),
    )

    assert response.status_code == 422


def test_너무_긴_여행은_422(client: TestClient) -> None:
    response = client.post(
        "/api/v1/routes",
        json=_manual_trip(endAt="2027-09-13T18:00:00+09:00"),
    )

    # 기간만큼 route_days 를 미리 만들기 때문에 상한이 필요하다.
    assert response.status_code == 422


def test_남의_반려동물은_데려갈_수_없다(
    client: TestClient, db: Session, stranger: User
) -> None:
    pet = Pet(id=uuid.uuid4(), user_id=stranger.id, name="남의 몽이", species=PetSpecies.DOG)
    db.add(pet)
    db.flush()

    response = client.post("/api/v1/routes", json=_manual_trip(petIds=[str(pet.id)]))

    assert response.status_code == 403


def test_내_반려동물은_여행에_붙는다(client: TestClient, db: Session, owner: User) -> None:
    pet = Pet(id=uuid.uuid4(), user_id=owner.id, name="몽이", species=PetSpecies.DOG)
    db.add(pet)
    db.flush()

    body = client.post("/api/v1/routes", json=_manual_trip(petIds=[str(pet.id)])).json()

    assert [p["name"] for p in body["pets"]] == ["몽이"]
