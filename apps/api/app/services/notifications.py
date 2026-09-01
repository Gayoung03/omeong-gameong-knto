"""DB 알림 저장과 Expo 푸시 발송의 단일 진입점."""

import logging
import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Notification, PushToken

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"
logger = logging.getLogger(__name__)


def add_notification(
    db: Session,
    *,
    user_id: uuid.UUID,
    type: str,
    target_id: uuid.UUID | None,
    title: str,
    content: str,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        type=type,
        target_id=target_id,
        title=title,
        content=content,
    )
    db.add(notification)
    return notification


def send_pushes(db: Session, notification: Notification) -> None:
    """푸시 실패가 완료 작업이나 DB 알림 저장을 되돌리지 않게 한다."""
    tokens = db.scalars(
        select(PushToken.token).where(PushToken.user_id == notification.user_id)
    ).all()
    if not tokens:
        return

    messages = [
        {
            "to": token,
            "title": notification.title,
            "body": notification.content,
            "data": {
                "type": notification.type,
                "targetId": str(notification.target_id) if notification.target_id else None,
            },
        }
        for token in tokens
    ]
    try:
        response = httpx.post(EXPO_PUSH_URL, json=messages, timeout=5)
        response.raise_for_status()
    except httpx.HTTPError:
        logger.exception(
            "Expo push delivery request failed",
            extra={"user_id": str(notification.user_id)},
        )
