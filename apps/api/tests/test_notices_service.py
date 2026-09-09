"""공지 발송 서비스 — 1회성 fan-out."""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Notice, Notification, User
from app.services.notices import announce_notice, create_and_publish_notice


@pytest.fixture(autouse=True)
def _no_push(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.notices.send_pushes", lambda db, n: None)


def _draft(db: Session) -> Notice:
    notice = Notice(
        id=uuid.uuid4(),
        title="점검 안내",
        content="내용",
        is_active=False,
        published_at=datetime.now(UTC),
    )
    db.add(notice)
    db.flush()
    return notice


def test_announce_once_then_noop(db: Session, owner: User) -> None:
    notice = _draft(db)

    def count() -> int:
        return db.scalar(
            select(func.count(Notification.id)).where(Notification.target_id == notice.id)
        )

    announce_notice(db, notice)
    first = count()
    assert first >= 1
    assert notice.announced_at is not None

    announce_notice(db, notice)
    assert count() == first  # 두 번째 호출은 아무것도 안 한다


def test_create_and_publish_inserts_active_and_announces(db: Session, owner: User) -> None:
    notice = create_and_publish_notice(db, title="새 공지", content="본문")

    assert notice.is_active is True
    assert notice.announced_at is not None
    assert db.scalar(
        select(func.count(Notification.id)).where(Notification.target_id == notice.id)
    ) >= 1
