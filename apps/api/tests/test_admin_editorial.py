import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import AdminEditorialAuditLog, EditorialStory, EditorialStorySource, User
from app.db.models.enums import EditorialStoryKind, EditorialStoryStatus


def _draft(db: Session) -> EditorialStory:
    story = EditorialStory(
        id=uuid.uuid4(),
        slug=f"admin-test-{uuid.uuid4().hex}",
        kind=EditorialStoryKind.EVENT,
        category="행사·특별 개방",
        card_title="제주 행사를 만나개",
        title="오늘 만나는 제주 특별 개방",
        summary="공식 안내를 확인하고 방문해 보세요.",
        hero_image_url="https://api.cdn.visitjeju.net/photo.webp",
        sections=[
            {
                "id": "section-1",
                "heading": "행사 소개",
                "paragraphs": ["제주의 특별한 행사를 소개해요."],
                "image_url": "https://api.cdn.visitjeju.net/detail.webp",
                "image_caption": "비짓제주 제공 이미지",
            }
        ],
        tips=["방문 전 공식 안내를 확인하개!"],
        tags=["제주", "행사"],
        status=EditorialStoryStatus.DRAFT,
        display_order=0,
    )
    db.add(story)
    db.flush()
    db.add(
        EditorialStorySource(
            id=uuid.uuid4(),
            story_id=story.id,
            provider="visitjeju",
            external_id=f"CONT_{uuid.uuid4().hex}",
            source_name="제주관광공사 비짓제주",
            source_title="비짓제주 원문 제목",
            source_url="https://www.visitjeju.net/kr/detail/view?contentsid=CONT_1",
            source_image_url="https://api.cdn.visitjeju.net/source.webp",
            source_published_at=datetime.now(UTC) - timedelta(days=2),
        )
    )
    db.flush()
    return story


def _make_admin(db: Session, user: User) -> None:
    user.is_admin = True
    db.flush()


def test_admin_endpoints_reject_regular_user(client: TestClient, db: Session) -> None:
    _draft(db)

    response = client.get("/api/v1/admin/editorial-stories")

    assert response.status_code == 403
    assert response.json()["detail"] == "관리자 권한이 필요합니다"


def test_admin_can_edit_publish_archive_and_restore_story(
    client: TestClient, db: Session, owner: User
) -> None:
    _make_admin(db, owner)
    story = _draft(db)

    # 초안은 관리자 목록에는 보이지만 공개 API에서는 숨겨진다.
    listed = client.get(
        "/api/v1/admin/editorial-stories",
        params={"status": "draft", "sortBy": "collected_at"},
    )
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["sourceNames"] == ["제주관광공사 비짓제주"]
    assert listed.json()["items"][0]["collectedAt"] is not None
    assert client.get("/api/v1/editorial-stories").json()["total"] == 0

    detail = client.get(f"/api/v1/admin/editorial-stories/{story.id}")
    assert detail.status_code == 200
    assert detail.json()["sources"][0]["sourceImageUrl"].endswith("source.webp")

    updated = client.patch(
        f"/api/v1/admin/editorial-stories/{story.id}",
        json={
            "cardTitle": "관리자가 다듬은 제주 행사",
            "summary": "공식 정보를 확인하고 자연스럽게 다듬었어요.",
            "displayOrder": 2,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["cardTitle"] == "관리자가 다듬은 제주 행사"
    assert updated.json()["auditLogs"][0]["action"] == "updated"

    published = client.post(f"/api/v1/admin/editorial-stories/{story.id}/publish", json={})
    assert published.status_code == 200
    assert published.json()["status"] == "published"
    assert published.json()["publishedAt"] is not None
    public_items = client.get("/api/v1/editorial-stories").json()["items"]
    assert [item["id"] for item in public_items] == [str(story.id)]

    cannot_edit = client.patch(
        f"/api/v1/admin/editorial-stories/{story.id}",
        json={"title": "게시 중 수정 시도"},
    )
    assert cannot_edit.status_code == 409

    archived = client.post(f"/api/v1/admin/editorial-stories/{story.id}/archive")
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"
    assert client.get("/api/v1/editorial-stories").json()["total"] == 0

    restored = client.post(f"/api/v1/admin/editorial-stories/{story.id}/draft")
    assert restored.status_code == 200
    assert restored.json()["status"] == "draft"
    assert restored.json()["publishedAt"] is None
    assert db.scalar(
        select(func.count(AdminEditorialAuditLog.id)).where(
            AdminEditorialAuditLog.story_id == story.id
        )
    ) == 4


def test_admin_publish_rejects_invalid_schedule(
    client: TestClient, db: Session, owner: User
) -> None:
    _make_admin(db, owner)
    story = _draft(db)
    story.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db.flush()

    response = client.post(f"/api/v1/admin/editorial-stories/{story.id}/publish", json={})

    assert response.status_code == 422
    assert response.json()["detail"] == "만료 시각은 게시 시각보다 늦어야 합니다"
