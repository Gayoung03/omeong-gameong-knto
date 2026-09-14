"""게시 승인된 제주 여행 이야기 공개 조회 API."""

import uuid
from collections import defaultdict
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.models import EditorialStory, EditorialStorySource
from app.db.models.enums import EditorialStoryKind, EditorialStoryStatus
from app.db.session import get_db
from app.schemas.editorial import (
    EditorialSourceResponse,
    EditorialStoryListResponse,
    EditorialStoryResponse,
)

router = APIRouter(prefix="/editorial-stories")
DbSession = Annotated[Session, Depends(get_db)]


def _visible_now(now: datetime):
    """승인 경계. draft·archived·게시 전·만료 글은 목록과 상세 모두에서 숨긴다.

    종류별 게시 글은 최대 1건이다 — 관리자 승인 API 가 같은 종류의 기존 게시 글을
    보관한 뒤 게시하므로(admin.publish_admin_editorial_story), 여기서 따로 중복을
    거르지 않아도 홈 `limit=4` 가 과거 같은 종류 글로 채워지지 않는다.
    """
    return (
        EditorialStory.status == EditorialStoryStatus.PUBLISHED,
        EditorialStory.published_at.isnot(None),
        EditorialStory.published_at <= now,
        or_(EditorialStory.expires_at.is_(None), EditorialStory.expires_at > now),
    )


def _reading_minutes(story: EditorialStory) -> int:
    characters = len(story.summary) + sum(
        len(paragraph)
        for section in story.sections
        for paragraph in section.get("paragraphs", [])
    )
    return max(1, round(characters / 500))


def _source_map(
    db: Session, story_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[EditorialSourceResponse]]:
    result: dict[uuid.UUID, list[EditorialSourceResponse]] = defaultdict(list)
    if not story_ids:
        return result
    sources = db.scalars(
        select(EditorialStorySource)
        .where(EditorialStorySource.story_id.in_(story_ids))
        .order_by(EditorialStorySource.collected_at)
    ).all()
    for source in sources:
        result[source.story_id].append(EditorialSourceResponse.model_validate(source))
    return result


def _response(
    story: EditorialStory, sources: list[EditorialSourceResponse]
) -> EditorialStoryResponse:
    return EditorialStoryResponse(
        id=story.id,
        slug=story.slug,
        kind=story.kind,
        category=story.category,
        card_title=story.card_title,
        title=story.title,
        summary=story.summary,
        hero_image_url=story.hero_image_url,
        published_at=story.published_at,
        reading_minutes=_reading_minutes(story),
        sections=story.sections,
        tips=story.tips,
        tags=story.tags,
        sources=sources,
    )


@router.get("", response_model=EditorialStoryListResponse, summary="게시된 제주 여행 이야기")
def list_editorial_stories(
    db: DbSession,
    kind: EditorialStoryKind | None = None,
    limit: Annotated[int, Query(ge=1, le=20)] = 4,
) -> EditorialStoryListResponse:
    now = datetime.now(UTC)
    conditions = list(_visible_now(now))
    if kind is not None:
        conditions.append(EditorialStory.kind == kind)
    total = db.scalar(select(func.count(EditorialStory.id)).where(*conditions)) or 0
    stories = db.scalars(
        select(EditorialStory)
        .where(*conditions)
        .order_by(EditorialStory.display_order, EditorialStory.published_at.desc())
        .limit(limit)
    ).all()
    sources = _source_map(db, [story.id for story in stories])
    return EditorialStoryListResponse(
        items=[_response(story, sources[story.id]) for story in stories], total=total
    )


@router.get("/{story_id}", response_model=EditorialStoryResponse, summary="제주 여행 이야기 상세")
def get_editorial_story(story_id: uuid.UUID, db: DbSession) -> EditorialStoryResponse:
    story = db.scalar(
        select(EditorialStory).where(
            EditorialStory.id == story_id,
            *_visible_now(datetime.now(UTC)),
        )
    )
    if story is None:
        raise HTTPException(status_code=404, detail="이야기를 찾을 수 없습니다")
    return _response(story, _source_map(db, [story.id])[story.id])
