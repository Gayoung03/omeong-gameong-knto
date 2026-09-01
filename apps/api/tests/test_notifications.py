"""알림함과 푸시 토큰의 최소 계약."""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Notification, PushToken, User


def _notification(user: User, *, title: str = "완료") -> Notification:
    return Notification(
        user_id=user.id,
        type="route_ready",
        target_id=uuid.uuid4(),
        title=title,
        content="일정을 확인해보세요.",
    )


def test_내_알림만_조회하고_읽음_처리한다(
    client: TestClient, db: Session, owner: User, stranger: User
) -> None:
    mine = _notification(owner)
    db.add_all([mine, _notification(stranger, title="남의 알림")])
    db.commit()

    body = client.get("/api/v1/notifications").json()
    assert body["total"] == 1
    assert body["items"][0]["targetId"] == str(mine.target_id)
    assert client.get("/api/v1/notifications/unread-count").json() == {"count": 1}

    read = client.patch(f"/api/v1/notifications/{mine.id}/read").json()
    assert read["isRead"] is True
    assert read["readAt"] is not None


def test_푸시_토큰은_같은_기기에서_중복되지_않는다(
    client: TestClient, db: Session, owner: User
) -> None:
    payload = {"token": "ExponentPushToken[test-device-token]", "platform": "ios"}
    assert client.post("/api/v1/push-tokens", json=payload).status_code == 204
    assert client.post("/api/v1/push-tokens", json=payload).status_code == 204

    tokens = db.scalars(select(PushToken).where(PushToken.user_id == owner.id)).all()
    assert len(tokens) == 1

    assert client.request("DELETE", "/api/v1/push-tokens", json=payload).status_code == 204
    assert db.scalar(select(PushToken).where(PushToken.user_id == owner.id)) is None
