"""비짓제주 공식 데이터 → AI 초안 → DB 적재 (Railway Cron 일일 배치).

**초안(draft)만 만든다.** 게시는 관리자 publish API에서만 한다.

같은 KST 날짜에 다시 실행해도 안전하다. 날짜+종류(kind)별로 하루 1건만 만들고,
이미 있는 종류는 비짓제주 상세 조회·OpenAI 호출 전에 건너뛴다. 이미 저장된 행은
어떤 필드도 수정하지 않는다.

    .venv/bin/python -m scripts.sync_editorial_stories   # Railway Cron (0 0 * * * UTC)
    uv run python -m scripts.sync_editorial_stories      # 로컬
"""

import argparse
import re
import uuid
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import EditorialStory, EditorialStorySource
from app.db.models.enums import EditorialStoryKind, EditorialStoryStatus
from app.db.session import SessionLocal
from app.integrations.visitjeju import (
    VisitJejuAPIError,
    fetch_all_contents,
    fetch_content_detail,
)
from app.integrations.weather.kma import WeatherForecastError, get_current_weather
from app.services.editorial_drafting import create_story_draft, select_daily_candidates

KST = timezone(timedelta(hours=9))


@dataclass
class SyncResult:
    created: list[EditorialStoryKind] = field(default_factory=list)
    skipped: list[EditorialStoryKind] = field(default_factory=list)
    failed: list[EditorialStoryKind] = field(default_factory=list)


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")[:160]


def _kind_prefix(day: date, kind: EditorialStoryKind) -> str:
    """slug 는 `{KST날짜}-{kind}-{원문id}` 형식이다. 앞 두 부분이 하루 1건의 기준."""
    return f"{day.isoformat()}-{kind.value}-"


def _existing_kinds(db: Session, day: date) -> set[EditorialStoryKind]:
    """그날 이미 만든 종류. 상태(draft/published/archived)와 무관하게 '있음'으로 본다."""
    return {
        kind
        for kind in EditorialStoryKind
        if db.scalar(
            select(EditorialStory.id)
            .where(EditorialStory.slug.startswith(_kind_prefix(day, kind)))
            .limit(1)
        )
        is not None
    }


def _weather() -> tuple[str, str]:
    try:
        current = get_current_weather(33.4996, 126.5312)
        return current.condition, (
            f"제주 현재 {current.condition}, {current.temperature:.0f}도, "
            f"강수확률 {current.precipitation_probability}%, 풍속 {current.wind_speed:.1f}m/s"
        )
    except WeatherForecastError:
        return "cloudy", "실시간 날씨를 확인하지 못했으므로 방문 직전 기상정보 확인 필요"


def _insert_draft(db: Session, candidate, draft, *, day: date) -> EditorialStory:
    """새 초안 행만 만든다. 기존 행을 조회·갱신하는 경로는 두지 않는다."""
    story = EditorialStory(
        id=uuid.uuid4(),
        slug=_slug(f"{_kind_prefix(day, candidate.kind)}{candidate.source.content_id}"),
        kind=candidate.kind,
        category=candidate.category,
        card_title=draft.card_title,
        title=draft.title,
        summary=draft.summary,
        hero_image_url=candidate.source.image_url,
        sections=draft.sections,
        tips=draft.tips,
        tags=draft.tags,
        display_order=candidate.display_order,
        generated_by_ai=True,
        generation_model=draft.model,
        status=EditorialStoryStatus.DRAFT,
        published_at=None,
        expires_at=(
            datetime.combine(day + timedelta(days=1), time.min, tzinfo=KST).astimezone(UTC)
            if candidate.kind == EditorialStoryKind.WEATHER
            else None
        ),
    )
    db.add(story)
    db.flush()
    db.add(
        EditorialStorySource(
            id=uuid.uuid4(),
            story_id=story.id,
            provider="visitjeju",
            external_id=candidate.source.content_id,
            source_name="제주관광공사 비짓제주",
            source_title=candidate.source.title,
            source_url=candidate.source.source_url,
            source_image_url=candidate.source.image_url,
        )
    )
    return story


def sync_daily_stories(db: Session, *, day: date, max_pages: int = 100) -> SyncResult:
    result = SyncResult()
    existing = _existing_kinds(db, day)
    result.skipped = [kind for kind in EditorialStoryKind if kind in existing]
    if len(existing) == len(EditorialStoryKind):
        return result

    condition, weather_summary = _weather()
    contents = fetch_all_contents(max_pages=max(1, max_pages))
    candidates = select_daily_candidates(contents, day=day, weather_condition=condition)
    found = {candidate.kind for candidate in candidates}
    result.failed = [
        kind for kind in EditorialStoryKind if kind not in existing and kind not in found
    ]

    for candidate in candidates:
        if candidate.kind in existing:
            continue
        try:
            candidate = replace(candidate, source=fetch_content_detail(candidate.source))
        except VisitJejuAPIError as error:
            print(f"상세 정보 생략: {candidate.source.title} ({error})")
        try:
            draft = create_story_draft(candidate, weather_summary=weather_summary)
        except Exception as error:  # noqa: BLE001 - 한 종류 실패가 나머지를 막지 않게
            print(f"초안 생성 실패: {candidate.kind.value} ({error})")
            result.failed.append(candidate.kind)
            continue
        # OpenAI 호출 사이에 다른 실행이 같은 종류를 저장했을 수 있다.
        if candidate.kind in _existing_kinds(db, day):
            result.skipped.append(candidate.kind)
            continue
        story = _insert_draft(db, candidate, draft, day=day)
        db.commit()
        result.created.append(candidate.kind)
        print(f"draft: {story.title}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="오늘(KST)의 제주 여행 이야기 초안 생성")
    parser.add_argument("--max-pages", type=int, default=100)
    args = parser.parse_args()
    day = datetime.now(KST).date()

    with SessionLocal() as db:
        try:
            result = sync_daily_stories(db, day=day, max_pages=args.max_pages)
        except VisitJejuAPIError as error:
            raise SystemExit(str(error)) from None

    print(
        f"{day.isoformat()} 생성 {len(result.created)} · 건너뜀 {len(result.skipped)}"
        f" · 실패 {len(result.failed)}"
    )
    if result.failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
