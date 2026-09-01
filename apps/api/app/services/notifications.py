"""DB 알림 저장과 모바일·웹 푸시 발송의 단일 진입점."""

import json
import logging
import uuid

import httpx
from pywebpush import WebPushException, webpush
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
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
    tokens = db.scalars(select(PushToken).where(PushToken.user_id == notification.user_id)).all()
    if not tokens:
        return

    mobile_tokens = [token.token for token in tokens if token.platform in {"ios", "android"}]
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
        for token in mobile_tokens
    ]
    if messages:
        try:
            response = httpx.post(EXPO_PUSH_URL, json=messages, timeout=5)
            response.raise_for_status()
        except httpx.HTTPError:
            logger.exception(
                "Expo push delivery request failed",
                extra={"user_id": str(notification.user_id)},
            )

    if not (settings.web_push_vapid_private_key and settings.web_push_vapid_subject):
        return

    payload = json.dumps(
        {
            "title": notification.title,
            "body": notification.content,
            "data": {
                "type": notification.type,
                "targetId": str(notification.target_id) if notification.target_id else None,
            },
        }
    )
    stale: list[PushToken] = []
    for token in tokens:
        if token.platform != "web" or not token.p256dh or not token.auth:
            continue
        try:
            webpush(
                subscription_info={
                    "endpoint": token.token,
                    "keys": {"p256dh": token.p256dh, "auth": token.auth},
                },
                data=payload,
                vapid_private_key=settings.web_push_vapid_private_key,
                vapid_claims={"sub": settings.web_push_vapid_subject},
                timeout=5,
            )
        except WebPushException as error:
            if error.response is not None and error.response.status_code in {404, 410}:
                stale.append(token)
            else:
                logger.exception(
                    "Web push delivery request failed",
                    extra={"user_id": str(notification.user_id)},
                )
        except Exception:
            logger.exception(
                "Web push configuration or delivery failed",
                extra={"user_id": str(notification.user_id)},
            )
    if stale:
        for token in stale:
            db.delete(token)
        db.commit()
