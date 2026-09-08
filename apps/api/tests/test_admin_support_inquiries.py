"""관리자 1:1 문의 콘솔."""

import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import AdminInquiryAuditLog, Inquiry, Notification, User


def _make_admin(db: Session, user: User) -> None:
    user.is_admin = True
    db.flush()


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


def test_regular_user_gets_403(client: TestClient, db: Session, owner: User) -> None:
    _inquiry(db, owner)

    assert client.get("/api/v1/admin/inquiries").status_code == 403


def test_admin_list_filters_and_searches(
    client: TestClient, db: Session, owner: User, stranger: User
) -> None:
    _make_admin(db, owner)
    _inquiry(db, owner, category="pet", title="반려동물 프로필 오류")
    _inquiry(db, stranger, category="bug", title="지도 오류")
    _inquiry(
        db,
        stranger,
        category="account",
        status="completed",
        title="계정 문의",
        answer="처리했어요.",
        answered_at=datetime.now(UTC),
    )

    all_items = client.get("/api/v1/admin/inquiries").json()
    assert all_items["total"] == 3
    assert {item["askerNickname"] for item in all_items["items"]} == {"테스트주인", "남"}

    pending = client.get("/api/v1/admin/inquiries", params={"status": "pending"})
    assert pending.json()["total"] == 2

    by_category = client.get("/api/v1/admin/inquiries", params={"category": "bug"})
    assert by_category.json()["total"] == 1

    searched = client.get("/api/v1/admin/inquiries", params={"search": "지도"})
    assert searched.json()["total"] == 1
    assert searched.json()["items"][0]["title"] == "지도 오류"


def test_answer_sets_fields_audit_and_notification(
    client: TestClient, db: Session, owner: User, stranger: User
) -> None:
    _make_admin(db, owner)
    inquiry = _inquiry(db, stranger, category="pet")

    greeting = "남님, 안녕하세요.\n오멍가멍입니다."
    footer = "감사합니다.\n오멍가멍 드림"
    full = f"{greeting}\n\n8월 업데이트에서 수정되었습니다.\n\n{footer}"
    response = client.post(
        f"/api/v1/admin/inquiries/{inquiry.id}/answer",
        json={"answer": full},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    # 관리자가 보낸 답변 전체가 그대로 저장된다.
    assert body["answer"] == full
    assert body["answerTemplate"] == f"{greeting}\n\n\n\n{footer}"
    assert body["answeredAt"] is not None
    assert body["auditLogs"][0]["action"] == "answered"

    assert db.scalar(
        select(func.count(AdminInquiryAuditLog.id)).where(
            AdminInquiryAuditLog.inquiry_id == inquiry.id
        )
    ) == 1
    notification = db.scalar(
        select(Notification).where(
            Notification.user_id == stranger.id,
            Notification.type == "inquiry_answered",
        )
    )
    assert notification is not None
    assert notification.target_id == inquiry.id


def test_answer_respects_disabled_notification(
    client: TestClient, db: Session, owner: User, stranger: User
) -> None:
    _make_admin(db, owner)
    stranger.inquiry_answer_notification_enabled = False
    inquiry = _inquiry(db, stranger)

    client.post(
        f"/api/v1/admin/inquiries/{inquiry.id}/answer",
        json={"answer": "확인 후 답변드립니다."},
    )

    count = db.scalar(
        select(func.count(Notification.id)).where(
            Notification.user_id == stranger.id,
            Notification.type == "inquiry_answered",
        )
    )
    assert count == 0


def test_answer_already_completed_is_409(
    client: TestClient, db: Session, owner: User, stranger: User
) -> None:
    _make_admin(db, owner)
    inquiry = _inquiry(
        db,
        stranger,
        status="completed",
        answer="이미 답변",
        answered_at=datetime.now(UTC),
    )

    response = client.post(
        f"/api/v1/admin/inquiries/{inquiry.id}/answer",
        json={"answer": "두 번째 답변"},
    )

    assert response.status_code == 409


def test_draft_answer_uses_service(
    client: TestClient, db: Session, owner: User, stranger: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    _make_admin(db, owner)
    inquiry = _inquiry(db, stranger)

    from app.services import inquiry_drafting

    monkeypatch.setattr(
        inquiry_drafting,
        "draft_answer",
        lambda db, inq: inquiry_drafting.InquiryDraft(
            reply="안내 초안입니다.",
            used_context=["반려동물 프로필 가이드"],
            needs_human_review=False,
            model="gpt-4o-mini",
        ),
    )

    response = client.post(f"/api/v1/admin/inquiries/{inquiry.id}/draft-answer")

    assert response.status_code == 200
    body = response.json()
    assert body["reply"] == "안내 초안입니다."
    assert body["needsHumanReview"] is False
    # 초안은 저장하지 않는다.
    assert db.get(Inquiry, inquiry.id).answer is None


def test_draft_answer_daily_limit(
    client: TestClient,
    db: Session,
    owner: User,
    stranger: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _make_admin(db, owner)
    from app.core.config import settings
    from app.services import inquiry_drafting

    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "inquiry_draft_daily_limit", 2)
    monkeypatch.setattr(
        inquiry_drafting,
        "draft_answer",
        lambda db, inq: inquiry_drafting.InquiryDraft(
            reply="초안", used_context=[], needs_human_review=False, model="gpt-4o-mini"
        ),
    )

    for _ in range(2):
        inquiry = _inquiry(db, stranger)
        assert (
            client.post(f"/api/v1/admin/inquiries/{inquiry.id}/draft-answer").status_code == 200
        )

    blocked = _inquiry(db, stranger)
    assert client.post(f"/api/v1/admin/inquiries/{blocked.id}/draft-answer").status_code == 429
