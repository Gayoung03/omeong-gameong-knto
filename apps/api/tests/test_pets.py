"""반려동물 프로필 API 테스트."""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import Pet, User
from app.db.models.enums import PetSpecies


def _create(client: TestClient, name: str = "몽이", **changes: object) -> dict:
    payload = {
        "name": name,
        "species": "dog",
        "breed": "말티즈",
        "size": "small",
        "weightKg": 4.2,
        "birthDate": "2021-05-03",
    }
    payload.update(changes)
    response = client.post("/api/v1/pets", json=payload)
    assert response.status_code == 201
    return response.json()


def test_첫_반려동물만_대표가_되고_나이는_서버가_계산한다(client: TestClient) -> None:
    first = _create(client)
    second = _create(client, "코코")

    assert first["isPrimary"] is True
    assert second["isPrimary"] is False
    assert first["age"] == 5


def test_목록은_내_활성_반려동물만_페이지네이션한다(
    client: TestClient, db: Session, stranger: User
) -> None:
    mine = _create(client)
    db.add(Pet(id=uuid.uuid4(), user_id=stranger.id, name="남의 펫", species=PetSpecies.DOG))
    db.flush()

    body = client.get("/api/v1/pets", params={"limit": 1, "offset": 0}).json()

    assert body["total"] == 1
    assert [item["id"] for item in body["items"]] == [mine["id"]]


def test_기타_종에는_species_detail이_필수다(client: TestClient) -> None:
    missing = client.post("/api/v1/pets", json={"name": "햄찌", "species": "other"})
    invalid = client.post(
        "/api/v1/pets",
        json={"name": "몽이", "species": "dog", "speciesDetail": "햄스터"},
    )
    valid = client.post(
        "/api/v1/pets",
        json={"name": "햄찌", "species": "other", "speciesDetail": " 햄스터 "},
    )

    assert missing.status_code == 422
    assert invalid.status_code == 422
    assert valid.status_code == 201
    assert valid.json()["speciesDetail"] == "햄스터"


def test_다른_사용자의_반려동물은_수정하거나_삭제할_수_없다(
    client: TestClient, db: Session, stranger: User
) -> None:
    pet = Pet(id=uuid.uuid4(), user_id=stranger.id, name="남의 펫", species=PetSpecies.DOG)
    db.add(pet)
    db.flush()

    assert client.patch(f"/api/v1/pets/{pet.id}", json={"name": "훔친 이름"}).status_code == 403
    assert client.delete(f"/api/v1/pets/{pet.id}").status_code == 403


def test_종을_other에서_dog로_바꾸면_species_detail을_비운다(client: TestClient) -> None:
    pet = _create(client, "햄찌", species="other", speciesDetail="햄스터", breed=None)

    response = client.patch(f"/api/v1/pets/{pet['id']}", json={"species": "dog"})

    assert response.status_code == 200
    assert response.json()["speciesDetail"] is None


def test_대표를_삭제하면_다음_반려동물이_대표가_된다(client: TestClient) -> None:
    first = _create(client)
    second = _create(client, "코코")

    deleted = client.delete(f"/api/v1/pets/{first['id']}")
    active = client.get("/api/v1/pets").json()
    all_pets = client.get("/api/v1/pets", params={"includeDeleted": True}).json()

    assert deleted.status_code == 204
    assert [item["id"] for item in active["items"]] == [second["id"]]
    assert active["items"][0]["isPrimary"] is True
    assert all_pets["total"] == 2
    deleted_item = next(item for item in all_pets["items"] if item["id"] == first["id"])
    assert deleted_item["status"] == "deleted"
    assert client.delete(f"/api/v1/pets/{first['id']}").status_code == 404


def test_미래_생년월일과_음수_몸무게를_거부한다(client: TestClient) -> None:
    future = client.post(
        "/api/v1/pets", json={"name": "미래펫", "species": "dog", "birthDate": "2999-01-01"}
    )
    negative = client.post(
        "/api/v1/pets", json={"name": "가벼운펫", "species": "dog", "weightKg": -1}
    )

    assert future.status_code == 422
    assert negative.status_code == 422


def test_수정에서_필수값_null은_거부한다(client: TestClient) -> None:
    pet = _create(client, "필수값펫")

    assert client.patch(f"/api/v1/pets/{pet['id']}", json={"name": None}).status_code == 422
    assert client.patch(f"/api/v1/pets/{pet['id']}", json={"species": None}).status_code == 422
