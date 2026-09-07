import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import EditorialStory, EditorialStorySource
from app.db.models.enums import EditorialStoryKind, EditorialStoryStatus


def _story(db: Session, *, status=EditorialStoryStatus.PUBLISHED) -> EditorialStory:
    story = EditorialStory(
        id=uuid.uuid4(),
        slug=f"test-{uuid.uuid4().hex}",
        kind=EditorialStoryKind.EVENT,
        category="행사·특별 개방",
        card_title="특별한 제주를 만나개",
        title="오늘 만나는 제주 특별 개방",
        summary="공식 정보를 확인해 소개한다멍.",
        hero_image_url="https://api.cdn.visitjeju.net/photo.webp",
        sections=[{"id": "section-1", "heading": "소개", "paragraphs": ["본문"]}],
        tips=["방문 전 공식 안내를 확인하세요."],
        tags=["제주", "행사"],
        status=status,
        display_order=0,
        published_at=datetime.now(UTC) - timedelta(minutes=1),
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
            source_title="공식 행사",
            source_url="https://www.visitjeju.net/kr/detail/view?contentsid=CONT_1",
        )
    )
    db.flush()
    return story


def test_editorial_list_and_detail_only_expose_published(
    client: TestClient, db: Session
) -> None:
    published = _story(db)
    draft = _story(db, status=EditorialStoryStatus.DRAFT)

    response = client.get("/api/v1/editorial-stories")
    body = response.json()

    assert response.status_code == 200
    assert [item["id"] for item in body["items"]] == [str(published.id)]
    assert body["items"][0]["sources"][0]["sourceName"] == "제주관광공사 비짓제주"
    assert client.get(f"/api/v1/editorial-stories/{published.id}").status_code == 200
    assert client.get(f"/api/v1/editorial-stories/{draft.id}").status_code == 404
