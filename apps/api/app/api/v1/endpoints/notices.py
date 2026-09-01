"""공개 공지사항 조회 API."""

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.db.models import Notice
from app.db.session import get_db
from app.schemas.notice import NoticeDetail, NoticeListItem, NoticeListResponse

router = APIRouter(prefix="/notices")
DbSession = Annotated[Session, Depends(get_db)]


def _visible_now():
    return Notice.is_active.is_(True), Notice.published_at <= datetime.now(UTC)


@router.get("", response_model=NoticeListResponse)
def list_notices(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> NoticeListResponse:
    conditions = _visible_now()
    total = db.scalar(select(func.count(Notice.id)).where(*conditions)) or 0
    notices = db.scalars(
        select(Notice)
        .where(*conditions)
        .order_by(desc(Notice.is_pinned), desc(Notice.published_at))
        .limit(limit)
        .offset(offset)
    ).all()
    return NoticeListResponse(
        items=[NoticeListItem.model_validate(notice) for notice in notices],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{notice_id}", response_model=NoticeDetail)
def get_notice(notice_id: uuid.UUID, db: DbSession) -> NoticeDetail:
    notice = db.scalar(select(Notice).where(Notice.id == notice_id, *_visible_now()))
    if notice is None:
        raise HTTPException(status_code=404, detail="공지사항을 찾을 수 없습니다")
    return NoticeDetail.model_validate(notice)
