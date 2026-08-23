"""리뷰 테스트.

여기서 지키려는 것은 **평점을 흔드는 길을 막는 것**이다 —
같은 사람이 같은 장소에 연달아 쓰는 것(30일 제한), 남의 리뷰를 고치는 것,
그리고 탈퇴한 사람의 닉네임이 그대로 남는 것.
"""

import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import Pet, Place, Review, User
from app.db.models.enums import PetSpecies

KST = timezone(timedelta(hours=9))


def _write(client: TestClient, place: Place, **body: object) -> dict:
    payload = {"rating": 5} | body
    return client.post(f"/api/v1/places/{place.id}/reviews", json=payload).json()


# ---------------------------------------------------------------------------
# 30일 제한
# ---------------------------------------------------------------------------


def test_같은_장소에_연달아_쓰면_429(client: TestClient, place: Place) -> None:
    first = client.post(f"/api/v1/places/{place.id}/reviews", json={"rating": 5})
    second = client.post(f"/api/v1/places/{place.id}/reviews", json={"rating": 1})

    assert first.status_code == 201
    assert second.status_code == 429
    # 앱이 이 문구를 그대로 보여준다.
    assert second.json()["detail"] == "동일 장소 리뷰는 한 달에 한번만 가능해요"


def test_30일이_지나면_다시_쓸_수_있다(
    client: TestClient, db: Session, place: Place, owner: User
) -> None:
    old = Review(
        id=uuid.uuid4(),
        user_id=owner.id,
        place_id=place.id,
        rating=3,
        created_at=datetime.now(KST) - timedelta(days=31),
    )
    db.add(old)
    db.flush()

    response = client.post(f"/api/v1/places/{place.id}/reviews", json={"rating": 5})

    assert response.status_code == 201


def test_방금_쓴_리뷰는_수정됨이_아니다(client: TestClient, place: Place) -> None:
    created = _write(client, place)

    # 작성 시점에는 created_at 과 updated_at 이 같은 트랜잭션의 now() 라 같은 값이다.
    assert created["isEdited"] is False


def test_수정에는_기간_제한이_없다(
    client: TestClient, db: Session, place: Place, owner: User
) -> None:
    """어제 쓴 리뷰를 오늘 고친다.

    **어제로 만들어두는 것이 핵심이다.** PostgreSQL 의 `now()` 는 문장 시각이
    아니라 **트랜잭션 시작 시각**이라, 테스트 한 개가 트랜잭션 하나로 도는
    이 구조에서는 작성과 수정이 같은 값을 받는다. 실제 서비스에서는 두 요청이
    서로 다른 트랜잭션이라 문제가 없지만, 테스트에서는 시간차를 만들어줘야
    isEdited 계산을 확인할 수 있다.
    """
    yesterday = datetime.now(KST) - timedelta(days=1)
    review = Review(
        id=uuid.uuid4(),
        user_id=owner.id,
        place_id=place.id,
        rating=5,
        created_at=yesterday,
        updated_at=yesterday,
    )
    db.add(review)
    db.flush()

    response = client.patch(f"/api/v1/reviews/{review.id}", json={"rating": 4})

    assert response.status_code == 200
    assert response.json()["rating"] == 4
    # 수정하면 "수정됨"이 화면에 붙는다.
    assert response.json()["isEdited"] is True


# ---------------------------------------------------------------------------
# 소유권
# ---------------------------------------------------------------------------


def test_남의_리뷰는_못_고친다(
    client: TestClient, db: Session, place: Place, stranger: User
) -> None:
    other = Review(id=uuid.uuid4(), user_id=stranger.id, place_id=place.id, rating=2)
    db.add(other)
    db.flush()

    assert client.patch(f"/api/v1/reviews/{other.id}", json={"rating": 5}).status_code == 403
    assert client.delete(f"/api/v1/reviews/{other.id}").status_code == 403


def test_남의_반려동물은_못_붙인다(
    client: TestClient, db: Session, place: Place, stranger: User
) -> None:
    pet = Pet(id=uuid.uuid4(), user_id=stranger.id, name="남의 몽이", species=PetSpecies.DOG)
    db.add(pet)
    db.flush()

    response = client.post(
        f"/api/v1/places/{place.id}/reviews",
        json={"rating": 5, "petId": str(pet.id)},
    )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# 검증
# ---------------------------------------------------------------------------


def test_미래_방문일은_422(client: TestClient, place: Place) -> None:
    tomorrow = (datetime.now(KST).date() + timedelta(days=1)).isoformat()

    response = client.post(
        f"/api/v1/places/{place.id}/reviews",
        json={"rating": 5, "visitedAt": tomorrow},
    )

    assert response.status_code == 422


def test_별점_범위를_벗어나면_422(client: TestClient, place: Place) -> None:
    response = client.post(f"/api/v1/places/{place.id}/reviews", json={"rating": 6})

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# 이미지
# ---------------------------------------------------------------------------


def test_이미지는_보낸_순서대로_저장된다(client: TestClient, place: Place) -> None:
    created = _write(client, place, imageUrls=["https://a", "https://b"])

    assert [image["sortOrder"] for image in created["images"]] == [0, 1]
    assert [image["imageUrl"] for image in created["images"]] == ["https://a", "https://b"]


def test_이미지를_보내면_통째로_갈아끼운다(client: TestClient, place: Place) -> None:
    created = _write(client, place, imageUrls=["https://a", "https://b"])

    response = client.patch(
        f"/api/v1/reviews/{created['id']}", json={"imageUrls": ["https://c"]}
    )

    # 개별 이미지만 빼는 방식은 없다. 화면이 항상 전체 목록을 제출한다.
    assert [image["imageUrl"] for image in response.json()["images"]] == ["https://c"]


def test_이미지를_안_보내면_그대로_둔다(client: TestClient, place: Place) -> None:
    created = _write(client, place, imageUrls=["https://a"])

    response = client.patch(f"/api/v1/reviews/{created['id']}", json={"rating": 3})

    assert len(response.json()["images"]) == 1


# ---------------------------------------------------------------------------
# 목록과 요약
# ---------------------------------------------------------------------------


def test_별점_분포는_빈_칸도_0으로_채운다(
    client: TestClient, db: Session, place: Place, stranger: User
) -> None:
    _write(client, place, rating=5)
    db.add(Review(id=uuid.uuid4(), user_id=stranger.id, place_id=place.id, rating=3))
    db.flush()

    summary = client.get(f"/api/v1/places/{place.id}/reviews").json()["summary"]

    # 화면이 5~1 막대를 항상 그린다. 없는 별점이 빠지면 막대가 사라진다.
    assert summary["ratingDistribution"] == {"5": 1, "4": 0, "3": 1, "2": 0, "1": 0}
    assert summary["averageRating"] == 4.0
    assert summary["totalCount"] == 2


def test_탈퇴한_사용자는_익명으로_보인다(
    client: TestClient, db: Session, place: Place, stranger: User
) -> None:
    stranger.deleted_at = datetime.now(KST)
    db.add(Review(id=uuid.uuid4(), user_id=stranger.id, place_id=place.id, rating=4))
    db.flush()

    items = client.get(f"/api/v1/places/{place.id}/reviews").json()["items"]
    author = next(item["author"] for item in items if item["isMine"] is False)

    # 리뷰는 남기고 작성자만 익명으로. 함께 지우면 별점 평균이 흔들린다.
    assert author["nickname"] == "탈퇴한 사용자"
    assert author["profileImageUrl"] is None


def test_내_리뷰_목록에는_장소가_붙는다(client: TestClient, place: Place) -> None:
    _write(client, place, content="좋았어요")

    body = client.get("/api/v1/users/me/reviews").json()

    assert body["total"] == 1
    assert body["items"][0]["place"]["name"] == place.name
    # 작성자가 나인 게 자명해서 author 는 빠진다.
    assert "author" not in body["items"][0]


def test_삭제하면_장소_평점이_다시_계산된다(client: TestClient, place: Place) -> None:
    created = _write(client, place, rating=5)
    assert client.get(f"/api/v1/places/{place.id}").json()["rating"] == 5.0

    client.delete(f"/api/v1/reviews/{created['id']}")

    body = client.get(f"/api/v1/places/{place.id}").json()
    # 저장된 값이 아니라 조회 시 집계라 따로 갱신할 것이 없다.
    assert body["reviewCount"] == 0
    assert body["rating"] is None


def test_방문일은_날짜다(client: TestClient, place: Place) -> None:
    created = _write(client, place, visitedAt="2026-07-15")

    assert created["visitedAt"] == "2026-07-15"
    assert date.fromisoformat(created["visitedAt"]) == date(2026, 7, 15)
