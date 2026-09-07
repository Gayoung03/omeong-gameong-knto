"""1:1 문의 사용자 API."""

import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import Inquiry, User


def _inquiry(db: Session, user: User, **overrides: object) -> Inquiry:
    inquiry = Inquiry(
        id=uuid.uuid4(),
        user_id=user.id,
        category=overrides.get("category", "pet"),
        status=overrides.get("status", "pending"),
        title=overrides.get("title", "반려동물 정보를 수정할 수 없어요"),
        content=overrides.get("content", "저장 버튼이 눌리지 않습니다."),
        answer=overrides.get("answer"),
        answered_at=overrides.get("answered_at"),
    )
    db.add(inquiry)
    db.flush()
    return inquiry


def test_create_inquiry_forces_pending(client: TestClient) -> None:
    response = client.post(
        "/api/v1/inquiries",
        json={
            "category": "bug",
            "title": "지도가 안 떠요",
            "content": "코스 상세에서 지도가 비어 있어요.",
            "status": "completed",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert body["answer"] is None
    assert body["imageUrls"] == []


def test_list_returns_only_my_inquiries_without_content(
    client: TestClient, db: Session, owner: User, stranger: User
) -> None:
    _inquiry(db, owner, title="내 문의")
    _inquiry(db, stranger, title="남의 문의")

    response = client.get("/api/v1/inquiries")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "내 문의"
    assert "content" not in body["items"][0]
    assert "answer" not in body["items"][0]


def test_list_status_filter(client: TestClient, db: Session, owner: User) -> None:
    _inquiry(db, owner, status="pending")
    _inquiry(
        db,
        owner,
        status="completed",
        answer="처리했어요.",
        answered_at=datetime.now(UTC),
    )

    pending = client.get("/api/v1/inquiries", params={"status": "pending"})
    completed = client.get("/api/v1/inquiries", params={"status": "completed"})

    assert pending.json()["total"] == 1
    assert completed.json()["total"] == 1
    assert completed.json()["items"][0]["answeredAt"] is not None


def test_detail_rejects_other_users_inquiry(
    client: TestClient, db: Session, stranger: User
) -> None:
    inquiry = _inquiry(db, stranger)

    response = client.get(f"/api/v1/inquiries/{inquiry.id}")

    assert response.status_code == 403


def test_detail_missing_is_404(client: TestClient) -> None:
    response = client.get(f"/api/v1/inquiries/{uuid.uuid4()}")

    assert response.status_code == 404
