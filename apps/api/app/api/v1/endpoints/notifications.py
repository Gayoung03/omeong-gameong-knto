"""내 알림함과 기기 푸시 토큰 API."""

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.db.models import Notification, PushToken
from app.db.session import get_db
from app.schemas.notification import (
    NotificationItem,
    NotificationListResponse,
    PushTokenCreate,
    PushTokenDelete,
    UnreadCountResponse,
)

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/notifications", response_model=NotificationListResponse)
def list_notifications(
    current_user: CurrentUser,
    db: DbSession,
    is_read: Annotated[bool | None, Query(alias="isRead")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> NotificationListResponse:
    conditions = [Notification.user_id == current_user.id]
    if is_read is not None:
        conditions.append(Notification.is_read == is_read)
    total = db.scalar(select(func.count(Notification.id)).where(*conditions)) or 0
    items = db.scalars(
        select(Notification)
        .where(*conditions)
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return NotificationListResponse(
        items=[NotificationItem.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/notifications/unread-count", response_model=UnreadCountResponse)
def unread_count(current_user: CurrentUser, db: DbSession) -> UnreadCountResponse:
    count = (
        db.scalar(
            select(func.count(Notification.id)).where(
                Notification.user_id == current_user.id, Notification.is_read.is_(False)
            )
        )
        or 0
    )
    return UnreadCountResponse(count=count)


@router.patch("/notifications/{notification_id}/read", response_model=NotificationItem)
def read_notification(
    notification_id: uuid.UUID, current_user: CurrentUser, db: DbSession
) -> NotificationItem:
    notification = db.get(Notification, notification_id)
    if notification is None:
        raise HTTPException(status_code=404, detail="알림을 찾을 수 없습니다")
    if notification.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="다른 사용자의 알림입니다")
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = datetime.now(UTC)
        db.commit()
        db.refresh(notification)
    return NotificationItem.model_validate(notification)


@router.post("/notifications/read-all", status_code=status.HTTP_204_NO_CONTENT)
def read_all_notifications(current_user: CurrentUser, db: DbSession) -> Response:
    now = datetime.now(UTC)
    db.execute(
        update(Notification)
        .where(Notification.user_id == current_user.id, Notification.is_read.is_(False))
        .values(is_read=True, read_at=now)
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/push-tokens", status_code=status.HTTP_204_NO_CONTENT)
def register_push_token(
    payload: PushTokenCreate, current_user: CurrentUser, db: DbSession
) -> Response:
    token = db.scalar(select(PushToken).where(PushToken.token == payload.token))
    if token is None:
        token = PushToken(user_id=current_user.id, token=payload.token, platform=payload.platform)
        db.add(token)
    else:
        token.user_id = current_user.id
        token.platform = payload.platform
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/push-tokens", status_code=status.HTTP_204_NO_CONTENT)
def delete_push_token(
    payload: PushTokenDelete, current_user: CurrentUser, db: DbSession
) -> Response:
    token = db.scalar(
        select(PushToken).where(
            PushToken.token == payload.token, PushToken.user_id == current_user.id
        )
    )
    if token is not None:
        db.delete(token)
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
