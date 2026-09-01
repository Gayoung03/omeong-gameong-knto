"""공지 발행과 전 사용자 알림 생성."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Notice, User
from app.services.notifications import add_notification, send_pushes


def publish_notice(db: Session, *, title: str, content: str, is_pinned: bool = False) -> Notice:
    notice = Notice(
        title=title,
        content=content,
        is_pinned=is_pinned,
        published_at=datetime.now(UTC),
    )
    db.add(notice)
    db.flush()

    notifications = [
        add_notification(
            db,
            user_id=user_id,
            type="notice",
            target_id=notice.id,
            title="새 공지사항이 등록됐어요",
            content=title,
        )
        for user_id in db.scalars(select(User.id).where(User.deleted_at.is_(None)))
    ]
    db.commit()
    # ponytail: 사용자 수가 커지면 outbox worker로 일괄 발송한다.
    for notification in notifications:
        send_pushes(db, notification)
    return notice
