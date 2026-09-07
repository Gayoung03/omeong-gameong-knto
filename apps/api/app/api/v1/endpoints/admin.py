"""관리자 전용 API.

모든 엔드포인트는 ``CurrentAdmin``을 요구한다. 공개 여행 이야기 API와
라우터부터 분리해 draft·archived가 일반 사용자 경로로 새지 않게 한다.
"""

import uuid
from collections import defaultdict
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentAdmin
from app.db.models import (
    AdminEditorialAuditLog,
    EditorialStory,
    EditorialStorySource,
)
from app.db.models.enums import EditorialStoryStatus
from app.db.session import get_db
from app.schemas.admin_editorial import (
    AdminEditorialAuditResponse,
    AdminEditorialOrder,
    AdminEditorialPublishRequest,
    AdminEditorialSort,
    AdminEditorialSourceResponse,
    AdminEditorialStoryDetail,
    AdminEditorialStoryListItem,
    AdminEditorialStoryListResponse,
    AdminEditorialStoryUpdate,
    AdminUserResponse,
)
from app.services.admin_audit import json_value as _json_value

router = APIRouter(prefix="/admin")
DbSession = Annotated[Session, Depends(get_db)]


def _story_or_404(db: Session, story_id: uuid.UUID, *, lock: bool = False) -> EditorialStory:
    query = select(EditorialStory).where(EditorialStory.id == story_id)
    if lock:
        query = query.with_for_update()
    story = db.scalar(query)
    if story is None:
        raise HTTPException(status_code=404, detail="이야기를 찾을 수 없습니다")
    return story


def _sources_by_story(
    db: Session, story_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[EditorialStorySource]]:
    result: dict[uuid.UUID, list[EditorialStorySource]] = defaultdict(list)
    if not story_ids:
        return result
    sources = db.scalars(
        select(EditorialStorySource)
        .where(EditorialStorySource.story_id.in_(story_ids))
        .order_by(EditorialStorySource.collected_at.desc())
    ).all()
    for source in sources:
        result[source.story_id].append(source)
    return result


def _audit(
    db: Session,
    *,
    story: EditorialStory,
    actor_id: uuid.UUID,
    action: str,
    previous_status: EditorialStoryStatus | None = None,
    next_status: EditorialStoryStatus | None = None,
    changes: dict | None = None,
) -> None:
    db.add(
        AdminEditorialAuditLog(
            story_id=story.id,
            actor_user_id=actor_id,
            action=action,
            previous_status=previous_status.value if previous_status else None,
            next_status=next_status.value if next_status else None,
            changes=changes or {},
        )
    )


def _detail(db: Session, story: EditorialStory) -> AdminEditorialStoryDetail:
    sources = _sources_by_story(db, [story.id])[story.id]
    audit_logs = db.scalars(
        select(AdminEditorialAuditLog)
        .where(AdminEditorialAuditLog.story_id == story.id)
        .order_by(AdminEditorialAuditLog.created_at.desc())
        .limit(30)
    ).all()
    return AdminEditorialStoryDetail(
        id=story.id,
        slug=story.slug,
        kind=story.kind,
        category=story.category,
        card_title=story.card_title,
        title=story.title,
        summary=story.summary,
        hero_image_url=story.hero_image_url,
        sections=story.sections,
        tips=story.tips,
        tags=story.tags,
        status=story.status,
        display_order=story.display_order,
        generated_by_ai=story.generated_by_ai,
        generation_model=story.generation_model,
        published_at=story.published_at,
        expires_at=story.expires_at,
        created_at=story.created_at,
        updated_at=story.updated_at,
        sources=[AdminEditorialSourceResponse.model_validate(source) for source in sources],
        audit_logs=[AdminEditorialAuditResponse.model_validate(log) for log in audit_logs],
    )


def _validate_schedule(
    *, published_at: datetime | None, expires_at: datetime | None
) -> None:
    if published_at is not None and expires_at is not None and expires_at <= published_at:
        raise HTTPException(
            status_code=422,
            detail="만료 시각은 게시 시각보다 늦어야 합니다",
        )


@router.get("/me", response_model=AdminUserResponse, summary="관리자 세션 확인")
def get_admin_me(current_admin: CurrentAdmin) -> AdminUserResponse:
    return AdminUserResponse.model_validate(current_admin)


@router.get(
    "/editorial-stories",
    response_model=AdminEditorialStoryListResponse,
    summary="관리자 여행 이야기 목록",
)
def list_admin_editorial_stories(
    db: DbSession,
    _current_admin: CurrentAdmin,
    story_status: Annotated[EditorialStoryStatus | None, Query(alias="status")] = None,
    sort_by: Annotated[AdminEditorialSort, Query(alias="sortBy")] = "collected_at",
    order: AdminEditorialOrder = "desc",
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
) -> AdminEditorialStoryListResponse:
    conditions = []
    if story_status is not None:
        conditions.append(EditorialStory.status == story_status)

    total = db.scalar(select(func.count(EditorialStory.id)).where(*conditions)) or 0
    collected_at = (
        select(func.max(EditorialStorySource.collected_at))
        .where(EditorialStorySource.story_id == EditorialStory.id)
        .correlate(EditorialStory)
        .scalar_subquery()
    )
    sort_column = collected_at if sort_by == "collected_at" else EditorialStory.published_at
    direction = desc if order == "desc" else asc
    stories = db.scalars(
        select(EditorialStory)
        .where(*conditions)
        .order_by(direction(sort_column).nulls_last(), EditorialStory.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()
    source_map = _sources_by_story(db, [story.id for story in stories])

    return AdminEditorialStoryListResponse(
        items=[
            AdminEditorialStoryListItem(
                id=story.id,
                slug=story.slug,
                kind=story.kind,
                category=story.category,
                card_title=story.card_title,
                title=story.title,
                status=story.status,
                source_names=list(
                    dict.fromkeys(source.source_name for source in source_map[story.id])
                ),
                collected_at=max(
                    (source.collected_at for source in source_map[story.id]), default=None
                ),
                published_at=story.published_at,
                expires_at=story.expires_at,
                created_at=story.created_at,
                updated_at=story.updated_at,
            )
            for story in stories
        ],
        total=total,
        page=page,
        limit=limit,
    )


@router.get(
    "/editorial-stories/{story_id}",
    response_model=AdminEditorialStoryDetail,
    summary="관리자 여행 이야기 상세",
)
def get_admin_editorial_story(
    story_id: uuid.UUID, db: DbSession, _current_admin: CurrentAdmin
) -> AdminEditorialStoryDetail:
    return _detail(db, _story_or_404(db, story_id))


@router.patch(
    "/editorial-stories/{story_id}",
    response_model=AdminEditorialStoryDetail,
    summary="여행 이야기 초안 수정",
)
def update_admin_editorial_story(
    story_id: uuid.UUID,
    payload: AdminEditorialStoryUpdate,
    db: DbSession,
    current_admin: CurrentAdmin,
) -> AdminEditorialStoryDetail:
    story = _story_or_404(db, story_id, lock=True)
    if story.status != EditorialStoryStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="초안 상태의 이야기만 수정할 수 있습니다",
        )

    values = payload.model_dump(exclude_unset=True)
    json_values = payload.model_dump(exclude_unset=True, mode="json")
    effective_published_at = values.get("published_at", story.published_at)
    effective_expires_at = values.get("expires_at", story.expires_at)
    _validate_schedule(
        published_at=effective_published_at,
        expires_at=effective_expires_at,
    )

    changes: dict[str, dict[str, object]] = {}
    for field, value in values.items():
        before = getattr(story, field)
        if before == value:
            continue
        changes[field] = {
            "before": _json_value(before),
            "after": json_values[field],
        }
        setattr(story, field, value)

    if changes:
        _audit(
            db,
            story=story,
            actor_id=current_admin.id,
            action="updated",
            changes=changes,
        )
        db.commit()
        db.refresh(story)
    return _detail(db, story)


@router.post(
    "/editorial-stories/{story_id}/publish",
    response_model=AdminEditorialStoryDetail,
    summary="여행 이야기 승인·게시",
)
def publish_admin_editorial_story(
    story_id: uuid.UUID,
    payload: AdminEditorialPublishRequest,
    db: DbSession,
    current_admin: CurrentAdmin,
) -> AdminEditorialStoryDetail:
    story = _story_or_404(db, story_id, lock=True)
    if story.status != EditorialStoryStatus.DRAFT:
        raise HTTPException(status_code=409, detail="초안만 게시할 수 있습니다")

    published_at = payload.published_at or story.published_at or datetime.now(UTC)
    _validate_schedule(published_at=published_at, expires_at=story.expires_at)
    previous_status = story.status
    story.status = EditorialStoryStatus.PUBLISHED
    story.published_at = published_at
    _audit(
        db,
        story=story,
        actor_id=current_admin.id,
        action="published",
        previous_status=previous_status,
        next_status=story.status,
        changes={"published_at": {"after": published_at.isoformat()}},
    )
    db.commit()
    db.refresh(story)
    return _detail(db, story)


@router.post(
    "/editorial-stories/{story_id}/archive",
    response_model=AdminEditorialStoryDetail,
    summary="여행 이야기 게시 중단·보관",
)
def archive_admin_editorial_story(
    story_id: uuid.UUID, db: DbSession, current_admin: CurrentAdmin
) -> AdminEditorialStoryDetail:
    story = _story_or_404(db, story_id, lock=True)
    if story.status != EditorialStoryStatus.PUBLISHED:
        raise HTTPException(status_code=409, detail="게시 중인 이야기만 보관할 수 있습니다")
    previous_status = story.status
    story.status = EditorialStoryStatus.ARCHIVED
    _audit(
        db,
        story=story,
        actor_id=current_admin.id,
        action="archived",
        previous_status=previous_status,
        next_status=story.status,
    )
    db.commit()
    db.refresh(story)
    return _detail(db, story)


@router.post(
    "/editorial-stories/{story_id}/draft",
    response_model=AdminEditorialStoryDetail,
    summary="보관 이야기를 초안으로 복귀",
)
def restore_admin_editorial_story_to_draft(
    story_id: uuid.UUID, db: DbSession, current_admin: CurrentAdmin
) -> AdminEditorialStoryDetail:
    story = _story_or_404(db, story_id, lock=True)
    if story.status != EditorialStoryStatus.ARCHIVED:
        raise HTTPException(
            status_code=409,
            detail="보관 상태의 이야기만 초안으로 돌릴 수 있습니다",
        )
    previous_status = story.status
    previous_published_at = story.published_at
    story.status = EditorialStoryStatus.DRAFT
    story.published_at = None
    _audit(
        db,
        story=story,
        actor_id=current_admin.id,
        action="restored_to_draft",
        previous_status=previous_status,
        next_status=story.status,
        changes={
            "published_at": {
                "before": _json_value(previous_published_at),
                "after": None,
            }
        },
    )
    db.commit()
    db.refresh(story)
    return _detail(db, story)
