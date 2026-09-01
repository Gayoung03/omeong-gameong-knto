"""알림함과 푸시 토큰의 최소 계약."""

import uuid
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Notification, PushToken, User
from app.services import notifications as notification_service


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


def test_웹_푸시_구독을_등록하고_해제한다(client: TestClient, db: Session, owner: User) -> None:
    payload = {
        "endpoint": "https://push.example.test/subscriptions/device-1234567890",
        "p256dh": "p256dh-test-key",
        "auth": "auth-test-key",
    }
    assert client.post("/api/v1/web-push/subscriptions", json=payload).status_code == 204

    token = db.scalar(select(PushToken).where(PushToken.user_id == owner.id))
    assert token is not None
    assert token.platform == "web"
    assert token.p256dh == payload["p256dh"]

    assert (
        client.request(
            "DELETE",
            "/api/v1/web-push/subscriptions",
            json={"endpoint": payload["endpoint"]},
        ).status_code
        == 204
    )
    assert db.scalar(select(PushToken).where(PushToken.user_id == owner.id)) is None


def test_모바일과_웹_푸시를_각_전송소로_나눠_보낸다(monkeypatch) -> None:
    user_id = uuid.uuid4()
    notification = Notification(
        user_id=user_id,
        type="notice",
        title="새 공지",
        content="내용을 확인해주세요.",
    )
    tokens = [
        PushToken(user_id=user_id, token="ExponentPushToken[test]", platform="ios"),
        PushToken(
            user_id=user_id,
            token="https://push.example.test/subscriptions/device",
            platform="web",
            p256dh="p256dh-test-key",
            auth="auth-test-key",
        ),
    ]
    db = MagicMock()
    db.scalars.return_value.all.return_value = tokens
    expo_post = MagicMock()
    expo_post.return_value.raise_for_status.return_value = None
    web_push = MagicMock()
    monkeypatch.setattr(notification_service.httpx, "post", expo_post)
    monkeypatch.setattr(notification_service, "webpush", web_push)
    monkeypatch.setattr(notification_service.settings, "web_push_vapid_private_key", "private")
    monkeypatch.setattr(
        notification_service.settings, "web_push_vapid_subject", "mailto:test@example.com"
    )

    notification_service.send_pushes(db, notification)

    assert expo_post.call_args.kwargs["json"][0]["to"] == "ExponentPushToken[test]"
    assert web_push.call_args.kwargs["subscription_info"]["endpoint"].startswith("https://push")
