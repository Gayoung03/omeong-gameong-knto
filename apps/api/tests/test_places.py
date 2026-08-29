"""장소 조회·즐겨찾기 테스트.

가장 크게 다루는 것은 **남이 등록한 장소가 새어 나오지 않는가**다.
`places` 한 테이블에 공식 장소와 사용자 장소가 함께 살아서, 조건 한 줄만
빠뜨려도 "우리 강아지 단골 카페" 같은 이름과 좌표가 전체 검색에 섞인다.
"""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import Place, PlacePetPolicy, User
from app.db.models.enums import DataProvider, PetPolicyType


def _make_place(db: Session, name: str, *, owner: User | None = None) -> Place:
    place = Place(
        id=uuid.uuid4(),
        name=name,
        category="cafe",
        latitude=33.4996,
        longitude=126.5312,
        created_by_user_id=owner.id if owner else None,
    )
    db.add(place)
    db.flush()
    return place


# ---------------------------------------------------------------------------
# 공식 장소와 나만의 장소의 분리
# ---------------------------------------------------------------------------


def test_남이_등록한_장소는_목록에_안_나온다(
    client: TestClient, db: Session, place: Place, stranger: User
) -> None:
    _make_place(db, "남의 단골 카페", owner=stranger)

    names = [item["name"] for item in client.get("/api/v1/places").json()["items"]]

    assert place.name in names
    assert "남의 단골 카페" not in names


def test_남이_등록한_장소는_상세도_404(
    client: TestClient, db: Session, stranger: User
) -> None:
    hidden = _make_place(db, "남의 단골 카페", owner=stranger)

    response = client.get(f"/api/v1/places/{hidden.id}")

    # 403 으로 알려주면 "그 id 의 장소가 존재한다"는 사실이 새어 나간다.
    assert response.status_code == 404


def test_내가_등록한_장소는_내_목록에만_나온다(
    client: TestClient, db: Session, owner: User
) -> None:
    mine = _make_place(db, "내 단골 카페", owner=owner)

    official = [item["name"] for item in client.get("/api/v1/places").json()["items"]]
    my_places = client.get("/api/v1/users/me/places").json()

    assert "내 단골 카페" not in official
    assert [item["name"] for item in my_places["items"]] == ["내 단골 카페"]
    # 태그·리뷰·거리는 내 장소에 붙지 않는다(명세).
    assert my_places["items"][0]["tags"] == []
    assert my_places["items"][0]["rating"] is None
    assert my_places["items"][0]["distanceMeters"] is None
    assert client.get(f"/api/v1/places/{mine.id}").status_code == 200


# ---------------------------------------------------------------------------
# 동반정책
# ---------------------------------------------------------------------------


def test_정책이_없는_장소도_unknown_으로_내려온다(client: TestClient, place: Place) -> None:
    body = client.get(f"/api/v1/places/{place.id}").json()

    # null 을 내리면 앱이 매번 존재 확인을 해야 하고 한 군데만 빠뜨려도 화면이 깨진다.
    assert body["petPolicy"]["policyType"] == "unknown"
    assert body["petPolicy"]["notes"] is None


def test_unknown_필터는_정책_행이_없는_장소도_잡는다(
    client: TestClient, db: Session, place: Place
) -> None:
    other = _make_place(db, "정책 있는 카페")
    db.add(
        PlacePetPolicy(
            place_id=other.id,
            policy_type=PetPolicyType.INDOOR_ALLOWED,
            source=DataProvider.INTERNAL,
        )
    )
    db.flush()

    names = [
        item["name"]
        for item in client.get("/api/v1/places", params={"petPolicy": "unknown"}).json()["items"]
    ]

    # 화면에는 "정보 없음"이라고 떠 있는데 필터에는 안 잡히면 안 된다.
    assert place.name in names
    assert "정책 있는 카페" not in names


# ---------------------------------------------------------------------------
# 즐겨찾기
# ---------------------------------------------------------------------------


def test_즐겨찾기는_여러_번_눌러도_같다(client: TestClient, place: Place) -> None:
    first = client.put(f"/api/v1/places/{place.id}/favorite")
    second = client.put(f"/api/v1/places/{place.id}/favorite")

    # 이미 즐겨찾기한 장소여도 409 가 아니라 204 다.
    assert first.status_code == 204
    assert second.status_code == 204

    favorites = client.get("/api/v1/users/me/favorites").json()
    assert favorites["total"] == 1
    assert favorites["items"][0]["isFavorite"] is True
    assert favorites["items"][0]["favoritedAt"] is not None


def test_즐겨찾기_해제는_안_한_장소에도_204(client: TestClient, place: Place) -> None:
    response = client.delete(f"/api/v1/places/{place.id}/favorite")

    assert response.status_code == 204
    assert client.get("/api/v1/users/me/favorites").json()["total"] == 0


def test_즐겨찾기_수는_상세에도_반영된다(client: TestClient, place: Place) -> None:
    client.put(f"/api/v1/places/{place.id}/favorite")

    body = client.get(f"/api/v1/places/{place.id}").json()

    assert body["savedCount"] == 1
    assert body["isFavorite"] is True


# ---------------------------------------------------------------------------
# 좌표
# ---------------------------------------------------------------------------


def test_좌표를_하나만_보내면_422(client: TestClient) -> None:
    response = client.get("/api/v1/places", params={"latitude": 33.5})

    assert response.status_code == 422


def test_공식_장소_목록은_limit_1000까지_허용한다(client: TestClient) -> None:
    assert client.get("/api/v1/places", params={"limit": 1000}).status_code == 200
    assert client.get("/api/v1/places", params={"limit": 1001}).status_code == 422


def test_반경_밖의_장소는_빠진다(client: TestClient, db: Session, place: Place) -> None:
    far = _make_place(db, "서울 카페")
    far.latitude = 37.5665
    far.longitude = 126.9780
    db.flush()

    body = client.get(
        "/api/v1/places",
        params={"latitude": 33.4996, "longitude": 126.5312, "radius": 50000},
    ).json()

    names = [item["name"] for item in body["items"]]
    assert "서울 카페" not in names
    assert place.name in names
    # 좌표를 보냈으니 거리가 채워진다.
    assert body["items"][0]["distanceMeters"] is not None


# ---------------------------------------------------------------------------
# 등록
# ---------------------------------------------------------------------------


def test_등록한_장소의_출처는_서버가_정한다(client: TestClient) -> None:
    response = client.post(
        "/api/v1/places",
        json={
            "name": "우리 강아지 단골 카페",
            "category": "cafe",
            "latitude": 33.4996,
            "longitude": 126.5312,
            "descriptionSource": "tour_api",
        },
    )

    assert response.status_code == 201
    # 앱이 출처를 정하게 두면 사용자 장소가 관광공사 데이터인 척할 수 있다.
    assert response.json()["descriptionSource"] == "internal"
    assert response.json()["isUserCreated"] is True


def test_좌표_범위를_벗어나면_422(client: TestClient) -> None:
    response = client.post(
        "/api/v1/places",
        json={"name": "달나라", "category": "etc", "latitude": 100.0, "longitude": 0.0},
    )

    assert response.status_code == 422
