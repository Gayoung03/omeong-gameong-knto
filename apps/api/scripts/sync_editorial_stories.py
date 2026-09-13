"""비짓제주 공식 데이터 → AI 초안 → DB 적재.

기본 실행은 검수 대기 초안만 만든다. 관리 페이지가 붙기 전 임시 승인이 필요할 때만
`--publish`를 명시한다. cron/Railway Scheduled Job에서 하루 한 번 실행해도 같은 날
같은 원문은 같은 slug로 갱신된다.

    uv run python -m scripts.sync_editorial_stories
    uv run python -m scripts.sync_editorial_stories --publish
"""

import argparse
import re
import uuid
from dataclasses import replace
from datetime import UTC, datetime, time, timedelta, timezone

from sqlalchemy import select, update

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


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")[:160]


def _weather() -> tuple[str, str]:
    try:
        current = get_current_weather(33.4996, 126.5312)
        return current.condition, (
            f"제주 현재 {current.condition}, {current.temperature:.0f}도, "
            f"강수확률 {current.precipitation_probability}%, 풍속 {current.wind_speed:.1f}m/s"
        )
    except WeatherForecastError:
        return "cloudy", "실시간 날씨를 확인하지 못했으므로 방문 직전 기상정보 확인 필요"


def _save_story(db, candidate, draft, *, day, publish: bool) -> EditorialStory:
    slug = _slug(f"{day.isoformat()}-{candidate.kind.value}-{candidate.source.content_id}")
    story = db.scalar(select(EditorialStory).where(EditorialStory.slug == slug))
    if story is None:
        story = EditorialStory(id=uuid.uuid4(), slug=slug)
        db.add(story)
    story.kind = candidate.kind
    story.category = candidate.category
    story.card_title = draft.card_title
    story.title = draft.title
    story.summary = draft.summary
    story.hero_image_url = candidate.source.image_url
    story.sections = draft.sections
    story.tips = draft.tips
    story.tags = draft.tags
    story.display_order = candidate.display_order
    story.generated_by_ai = True
    story.generation_model = draft.model
    story.status = EditorialStoryStatus.PUBLISHED if publish else EditorialStoryStatus.DRAFT
    story.published_at = datetime.now(UTC) if publish else None
    story.expires_at = (
        datetime.combine(day + timedelta(days=1), time.min, tzinfo=KST).astimezone(UTC)
        if candidate.kind == EditorialStoryKind.WEATHER
        else None
    )
    db.flush()

    source = db.scalar(
        select(EditorialStorySource).where(
            EditorialStorySource.story_id == story.id,
            EditorialStorySource.provider == "visitjeju",
            EditorialStorySource.external_id == candidate.source.content_id,
        )
    )
    if source is None:
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--publish", action="store_true", help="이번 결과를 즉시 게시")
    parser.add_argument("--max-pages", type=int, default=100)
    args = parser.parse_args()
    now = datetime.now(KST)
    condition, weather_summary = _weather()
    try:
        contents = fetch_all_contents(max_pages=max(1, args.max_pages))
    except VisitJejuAPIError as error:
        raise SystemExit(str(error)) from None
    candidates = select_daily_candidates(contents, day=now.date(), weather_condition=condition)
    if len(candidates) < 4:
        raise SystemExit(f"공식 이미지와 소개가 있는 콘텐츠가 부족합니다({len(candidates)}/4)")
    enriched_candidates = []
    for candidate in candidates:
        try:
            candidate = replace(candidate, source=fetch_content_detail(candidate.source))
        except VisitJejuAPIError as error:
            print(f"상세 정보 생략: {candidate.source.title} ({error})")
        enriched_candidates.append(candidate)
    candidates = enriched_candidates

    with SessionLocal() as db:
        for candidate in candidates:
            draft = create_story_draft(candidate, weather_summary=weather_summary)
            if args.publish:
                db.execute(
                    update(EditorialStory)
                    .where(
                        EditorialStory.kind == candidate.kind,
                        EditorialStory.status == EditorialStoryStatus.PUBLISHED,
                    )
                    .values(status=EditorialStoryStatus.ARCHIVED)
                )
            story = _save_story(
                db, candidate, draft, day=now.date(), publish=args.publish
            )
            print(f"{story.status.value}: {story.title}")
        db.commit()
    print(f"완료: {len(candidates)}건 ({'게시' if args.publish else '검수 대기'})")


if __name__ == "__main__":
    main()
