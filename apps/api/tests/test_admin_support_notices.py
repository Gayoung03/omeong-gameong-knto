"""관리자 공지사항 콘솔.

시드 데이터가 있는 DB 에서도 통과하도록 "이 공지"만 확인한다 —
전체 개수·전체 알림 수에 기대지 않는다.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Notification, User


@pytest.fixture(autouse=True)
def _no_push(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.notices.send_pushes", lambda db, n: None)


def _make_admin(db: Session, user: User) -> None:
    user.is_admin = True
    db.flush()


def _notice_count(db: Session, notice_id: str) -> int:
    return db.scalar(
        select(func.count(Notification.id)).where(Notification.target_id == notice_id)
    )


def _public_ids(client: TestClient) -> list[str]:
    return [item["id"] for item in client.get("/api/v1/notices?limit=100").json()["items"]]


def test_draft_is_hidden_from_public_and_not_announced(
    client: TestClient, db: Session, owner: User
) -> None:
    _make_admin(db, owner)

    created = client.post(
        "/api/v1/admin/notices",
        json={"title": "9월 점검 안내", "content": "새벽 2시 점검"},
    )
    assert created.status_code == 201
    notice_id = created.json()["id"]
    assert created.json()["isActive"] is False
    assert created.json()["announcedAt"] is None

    assert notice_id not in _public_ids(client)
    assert _notice_count(db, notice_id) == 0


def test_patch_edits_without_fanout(client: TestClient, db: Session, owner: User) -> None:
    _make_admin(db, owner)
    notice_id = client.post(
        "/api/v1/admin/notices", json={"title": "초안", "content": "내용"}
    ).json()["id"]

    patched = client.patch(
        f"/api/v1/admin/notices/{notice_id}",
        json={"title": "제목 수정", "isPinned": True},
    )
    assert patched.status_code == 200
    assert patched.json()["title"] == "제목 수정"
    assert patched.json()["isPinned"] is True
    assert patched.json()["auditLogs"][0]["action"] == "updated"
    assert _notice_count(db, notice_id) == 0


def test_publish_fans_out_once(
    client: TestClient, db: Session, owner: User, stranger: User
) -> None:
    _make_admin(db, owner)
    active_users = db.scalar(
        select(func.count(User.id)).where(User.deleted_at.is_(None))
    )
    notice_id = client.post(
        "/api/v1/admin/notices", json={"title": "공지", "content": "본문"}
    ).json()["id"]

    published = client.post(f"/api/v1/admin/notices/{notice_id}/publish", json={})
    assert published.status_code == 200
    assert published.json()["isActive"] is True
    assert published.json()["announcedAt"] is not None

    # 비삭제 사용자 한 명당 하나씩(owner·stranger 포함).
    assert _notice_count(db, notice_id) == active_users
    for user_id in (owner.id, stranger.id):
        assert db.scalar(
            select(func.count(Notification.id)).where(
                Notification.target_id == notice_id,
                Notification.user_id == user_id,
            )
        ) == 1
    assert notice_id in _public_ids(client)

    again = client.post(f"/api/v1/admin/notices/{notice_id}/publish", json={})
    assert again.status_code == 409
    assert _notice_count(db, notice_id) == active_users  # 재발송 없음


def test_unpublish_hides_but_keeps_announced_at(
    client: TestClient, db: Session, owner: User
) -> None:
    _make_admin(db, owner)
    notice_id = client.post(
        "/api/v1/admin/notices", json={"title": "공지", "content": "본문"}
    ).json()["id"]
    client.post(f"/api/v1/admin/notices/{notice_id}/publish", json={})
    assert notice_id in _public_ids(client)

    unpublished = client.post(f"/api/v1/admin/notices/{notice_id}/unpublish")
    assert unpublished.status_code == 200
    assert unpublished.json()["isActive"] is False
    assert unpublished.json()["announcedAt"] is not None

    assert notice_id not in _public_ids(client)

    # 재발행 시도는 여전히 막힌다(announced_at 유지).
    assert client.post(f"/api/v1/admin/notices/{notice_id}/publish", json={}).status_code == 409


def test_list_filter_tabs(client: TestClient, db: Session, owner: User) -> None:
    _make_admin(db, owner)
    draft_id = client.post(
        "/api/v1/admin/notices", json={"title": "초안 공지", "content": "x"}
    ).json()["id"]
    announced_id = client.post(
        "/api/v1/admin/notices", json={"title": "발송 공지", "content": "y"}
    ).json()["id"]
    client.post(f"/api/v1/admin/notices/{announced_id}/publish", json={})

    draft_ids = [
        item["id"]
        for item in client.get(
            "/api/v1/admin/notices", params={"filter": "draft", "limit": 100}
        ).json()["items"]
    ]
    announced_ids = [
        item["id"]
        for item in client.get(
            "/api/v1/admin/notices", params={"filter": "announced", "limit": 100}
        ).json()["items"]
    ]

    assert draft_id in draft_ids and draft_id not in announced_ids
    assert announced_id in announced_ids and announced_id not in draft_ids


def test_regular_user_gets_403(client: TestClient) -> None:
    assert client.get("/api/v1/admin/notices").status_code == 403
