"""사용자 프로필 API 테스트."""

import uuid
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import Favorite, Route, TravelLog, User
from app.db.models.enums import RouteStatus


def test_내_정보와_활동_요약을_조회한다(
    client: TestClient,
    db: Session,
    owner: User,
    place,
    trip: Route,
) -> None:
    trip.status = RouteStatus.SAVED
    db.add(Favorite(user_id=owner.id, place_id=place.id))
    db.add(
        TravelLog(
            id=uuid.uuid4(),
            user_id=owner.id,
            place_name_snapshot="협재해수욕장",
            recorded_date=date(2026, 8, 23),
            original_image_url="https://example.com/original.jpg",
            writing_style="dog_diary",
        )
    )
    db.flush()

    body = client.get("/api/v1/users/me").json()

    assert body["id"] == str(owner.id)
    assert body["status"] == "active"
    assert body["activitySummary"] == {
        "savedPlacesCount": 1,
        "savedRoutesCount": 1,
        "travelLogsCount": 1,
    }


def test_닉네임과_프로필_URL을_수정하고_초기화한다(client: TestClient) -> None:
    updated = client.patch(
        "/api/v1/users/me",
        json={"nickname": "  새 닉네임  ", "profileImageUrl": "https://example.com/me.jpg"},
    )

    assert updated.status_code == 200
    assert updated.json()["nickname"] == "새 닉네임"
    assert updated.json()["profileImageUrl"] == "https://example.com/me.jpg"

    reset = client.patch("/api/v1/users/me", json={"profileImageUrl": None})
    assert reset.status_code == 200
    assert reset.json()["profileImageUrl"] is None


def test_알림_설정은_보낸_필드만_수정한다(client: TestClient) -> None:
    response = client.patch(
        "/api/v1/users/me/notification-preferences",
        json={"marketingEnabled": True},
    )

    assert response.status_code == 200
    assert response.json() == {
        "inquiryAnswerEnabled": True,
        "marketingEnabled": True,
    }


def test_빈_닉네임은_거부한다(client: TestClient) -> None:
    assert client.patch("/api/v1/users/me", json={"nickname": "   "}).status_code == 422
    assert client.patch("/api/v1/users/me", json={"nickname": None}).status_code == 422


def test_알림_설정_null은_거부한다(client: TestClient) -> None:
    response = client.patch(
        "/api/v1/users/me/notification-preferences",
        json={"marketingEnabled": None},
    )
    assert response.status_code == 422
