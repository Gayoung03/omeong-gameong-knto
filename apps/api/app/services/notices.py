"""공지 발행과 전 사용자 알림 생성.

발송은 **한 번만** 한다. `notice.announced_at` 이 표식이다 — 채워져 있으면
이미 발송한 것이라 다시 보내지 않는다. 관리자 콘솔의 초안·수정·재게시는 모두
`announce_notice` 를 거치지 않고, `/publish` 만 거친다.
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Notice, User
from app.services.notifications import add_notification, send_pushes


def announce_notice(db: Session, notice: Notice) -> Notice:
    """공지를 전 사용자에게 알린다. 이미 발송했으면 아무것도 하지 않는다."""
    if notice.announced_at is not None:
        return notice

    notifications = [
        add_notification(
            db,
            user_id=user_id,
            type="notice",
            target_id=notice.id,
            title="새 공지사항이 등록됐어요",
            content=notice.title,
        )
        for user_id in db.scalars(select(User.id).where(User.deleted_at.is_(None)))
    ]
    notice.announced_at = datetime.now(UTC)
    db.commit()
    # ponytail: 사용자 수가 커지면 outbox worker로 일괄 발송한다.
    for notification in notifications:
        send_pushes(db, notification)
    return notice


def create_and_publish_notice(
    db: Session, *, title: str, content: str, is_pinned: bool = False
) -> Notice:
    """공지를 바로 공개하고 전 사용자에게 알린다(스크립트·기존 경로)."""
    notice = Notice(
        title=title,
        content=content,
        is_pinned=is_pinned,
        published_at=datetime.now(UTC),
    )
    db.add(notice)
    db.flush()
    return announce_notice(db, notice)


#: 기존 호출부 호환용 별칭. 새 코드는 create_and_publish_notice 를 쓴다.
publish_notice = create_and_publish_notice
