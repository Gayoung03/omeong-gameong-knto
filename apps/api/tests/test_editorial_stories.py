import inspect
import sys
import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import EditorialStory, EditorialStorySource, User
from app.db.models.enums import EditorialStoryKind, EditorialStoryStatus
from app.integrations.visitjeju import VisitJejuContent
from app.services.editorial_drafting import StoryDraft
from scripts import sync_editorial_stories as sync

# 다른 테스트 데이터와 slug 접두사가 겹치지 않는 먼 날짜
DAY = date(2031, 5, 5)


def _story(
    db: Session,
    *,
    status=EditorialStoryStatus.PUBLISHED,
    kind=EditorialStoryKind.EVENT,
    published_at: datetime | None = None,
    expires_at: datetime | None = None,
) -> EditorialStory:
    story = EditorialStory(
        id=uuid.uuid4(),
        slug=f"test-{uuid.uuid4().hex}",
        kind=kind,
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
        published_at=published_at or datetime.now(UTC) - timedelta(minutes=1),
        expires_at=expires_at,
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


def _ids(client: TestClient) -> list[str]:
    return [item["id"] for item in client.get("/api/v1/editorial-stories").json()["items"]]


# ---------------------------------------------------------------------------
# 공개 API — 승인 경계
# ---------------------------------------------------------------------------


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


def test_public_api_hides_draft_archived_future_and_expired(
    client: TestClient, db: Session
) -> None:
    now = datetime.now(UTC)
    hidden = [
        _story(db, status=EditorialStoryStatus.DRAFT, kind=EditorialStoryKind.EVENT),
        _story(db, status=EditorialStoryStatus.ARCHIVED, kind=EditorialStoryKind.STORY),
        _story(db, kind=EditorialStoryKind.GUIDE, published_at=now + timedelta(hours=1)),
        _story(
            db,
            kind=EditorialStoryKind.WEATHER,
            published_at=now - timedelta(days=1),
            expires_at=now - timedelta(minutes=1),
        ),
    ]

    assert _ids(client) == []
    for story in hidden:
        assert client.get(f"/api/v1/editorial-stories/{story.id}").status_code == 404


# ---------------------------------------------------------------------------
# 일일 배치 — 외부 호출은 전부 가짜
# ---------------------------------------------------------------------------


def _content(content_id: str, text: str) -> VisitJejuContent:
    return VisitJejuContent(
        content_id=content_id,
        title=text,
        category="관광지",
        introduction=f"{text} 공식 소개",
        tags=(text,),
        address="제주",
        image_url=f"https://api.cdn.visitjeju.net/{content_id}.webp",
        source_url=f"https://www.visitjeju.net/kr/detail/view?contentsid={content_id}",
    )


# rainy 날씨에서 행사·날씨·이야기·가이드 네 슬롯이 모두 채워지는 원문
CONTENTS_A = [
    _content("A1", "특별 개방 행사"),
    _content("A2", "실내 박물관"),
    _content("A3", "제주 바다 산책"),
    _content("A4", "유네스코 세계유산"),
]
CONTENTS_B = [
    _content("B1", "야간 개방 축제 행사"),
    _content("B2", "숲 산책 공원"),
    _content("B3", "제주 오름 여행"),
    _content("B4", "세계자연유산 오름"),
]


class FakeExternal:
    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.contents = CONTENTS_A
        self.condition = "rainy"
        self.fetch_calls = 0
        self.drafted: list[EditorialStoryKind] = []
        self.fail_kinds: set[EditorialStoryKind] = set()
        monkeypatch.setattr(sync, "_weather", lambda: (self.condition, "날씨 요약"))
        monkeypatch.setattr(sync, "fetch_all_contents", self._fetch)
        monkeypatch.setattr(sync, "fetch_content_detail", lambda content: content)
        monkeypatch.setattr(sync, "create_story_draft", self._draft)

    def _fetch(self, *, max_pages: int) -> list[VisitJejuContent]:
        self.fetch_calls += 1
        return self.contents

    def _draft(self, candidate, *, weather_summary: str | None) -> StoryDraft:
        self.drafted.append(candidate.kind)
        if candidate.kind in self.fail_kinds:
            raise RuntimeError("OpenAI 실패")
        return StoryDraft(
            card_title=f"AI 카드 {candidate.source.title}",
            title=f"AI 제목 {candidate.source.title}",
            summary="AI 요약이에요.",
            sections=[{"id": "section-1", "heading": "소개", "paragraphs": ["AI 본문"]}],
            tips=["팁"],
            tags=["제주"],
            model="fake-model",
        )


@pytest.fixture
def external(monkeypatch: pytest.MonkeyPatch) -> FakeExternal:
    return FakeExternal(monkeypatch)


def _day_stories(db: Session) -> list[EditorialStory]:
    return list(
        db.scalars(
            select(EditorialStory).where(EditorialStory.slug.startswith(f"{DAY.isoformat()}-"))
        ).all()
    )


def test_batch_creates_one_draft_per_kind(db: Session, external: FakeExternal) -> None:
    result = sync.sync_daily_stories(db, day=DAY)

    stories = _day_stories(db)
    assert sorted(result.created) == sorted(EditorialStoryKind)
    assert {story.kind for story in stories} == set(EditorialStoryKind)
    assert len(stories) == 4
    assert all(story.status == EditorialStoryStatus.DRAFT for story in stories)
    assert all(story.published_at is None for story in stories)


def test_same_day_rerun_skips_before_external_calls(
    db: Session, external: FakeExternal
) -> None:
    sync.sync_daily_stories(db, day=DAY)
    external.fetch_calls = 0
    external.drafted.clear()

    # 원문 후보와 날씨가 바뀌어도 같은 날 같은 종류는 추가되지 않는다.
    external.contents = CONTENTS_B
    external.condition = "sunny"
    result = sync.sync_daily_stories(db, day=DAY)

    assert len(_day_stories(db)) == 4
    assert result.created == []
    assert sorted(result.skipped) == sorted(EditorialStoryKind)
    assert external.fetch_calls == 0
    assert external.drafted == []


def test_rerun_keeps_admin_edits_and_published_state(
    client: TestClient, db: Session, owner: User, external: FakeExternal
) -> None:
    owner.is_admin = True
    db.flush()
    sync.sync_daily_stories(db, day=DAY)
    event = next(story for story in _day_stories(db) if story.kind == EditorialStoryKind.EVENT)

    assert client.patch(
        f"/api/v1/admin/editorial-stories/{event.id}", json={"title": "관리자가 고친 제목"}
    ).status_code == 200
    assert client.post(
        f"/api/v1/admin/editorial-stories/{event.id}/publish", json={}
    ).status_code == 200
    db.refresh(event)
    published_at = event.published_at

    external.contents = CONTENTS_B
    sync.sync_daily_stories(db, day=DAY)
    db.refresh(event)

    assert event.title == "관리자가 고친 제목"
    assert event.status == EditorialStoryStatus.PUBLISHED
    assert event.published_at == published_at
    assert len(_day_stories(db)) == 4


def test_batch_only_drafts_missing_kinds(db: Session, external: FakeExternal) -> None:
    existing = _story(db, status=EditorialStoryStatus.ARCHIVED, kind=EditorialStoryKind.EVENT)
    existing.slug = f"{DAY.isoformat()}-event-legacy"
    db.flush()

    result = sync.sync_daily_stories(db, day=DAY)

    assert EditorialStoryKind.EVENT not in external.drafted
    assert sorted(external.drafted) == sorted(
        kind for kind in EditorialStoryKind if kind != EditorialStoryKind.EVENT
    )
    assert result.skipped == [EditorialStoryKind.EVENT]
    assert db.scalar(
        select(func.count(EditorialStory.id)).where(
            EditorialStory.slug.startswith(f"{DAY.isoformat()}-event-")
        )
    ) == 1


def test_one_failed_kind_keeps_other_drafts(db: Session, external: FakeExternal) -> None:
    external.fail_kinds = {EditorialStoryKind.WEATHER}

    result = sync.sync_daily_stories(db, day=DAY)

    assert result.failed == [EditorialStoryKind.WEATHER]
    assert {story.kind for story in _day_stories(db)} == set(EditorialStoryKind) - {
        EditorialStoryKind.WEATHER
    }


def test_batch_has_no_publish_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["sync_editorial_stories", "--publish"])

    with pytest.raises(SystemExit) as exc:
        sync.main()

    assert exc.value.code == 2  # argparse: 알 수 없는 인자 — DB 접속 전에 종료
    # 배치 코드에는 게시 상태를 만드는 경로 자체가 없다.
    assert "EditorialStoryStatus.PUBLISHED" not in inspect.getsource(sync)


def test_home_shows_story_only_after_admin_approval(
    client: TestClient, db: Session, owner: User, external: FakeExternal
) -> None:
    owner.is_admin = True
    db.flush()
    sync.sync_daily_stories(db, day=DAY)
    stories = _day_stories(db)

    assert _ids(client) == []

    story = next(item for item in stories if item.kind == EditorialStoryKind.STORY)
    assert client.post(
        f"/api/v1/admin/editorial-stories/{story.id}/publish", json={}
    ).status_code == 200

    assert _ids(client) == [str(story.id)]
    assert client.get(f"/api/v1/editorial-stories/{story.id}").status_code == 200


def test_home_limit_never_filled_by_older_same_kind(
    client: TestClient, db: Session, owner: User
) -> None:
    owner.is_admin = True
    db.flush()
    for kind in EditorialStoryKind:
        first = _story(db, status=EditorialStoryStatus.DRAFT, kind=kind)
        second = _story(db, status=EditorialStoryStatus.DRAFT, kind=kind)
        for draft in (first, second):
            assert client.post(
                f"/api/v1/admin/editorial-stories/{draft.id}/publish", json={}
            ).status_code == 200

    items = client.get("/api/v1/editorial-stories", params={"limit": 4}).json()["items"]

    assert len(items) == 4
    assert sorted(item["kind"] for item in items) == sorted(
        kind.value for kind in EditorialStoryKind
    )
