"""1:1 문의 엔드포인트 (사용자용).

내 문의만 보고, 새로 쓰고, 상세를 연다. **작성 후 수정·삭제는 없다**
(docs/api/notifications.md). 관리자 답변은 `admin_support.py` 가 맡는다.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.db.models import Inquiry
from app.db.session import get_db
from app.schemas.inquiry import (
    InquiryCreate,
    InquiryDetail,
    InquiryListItem,
    InquiryListResponse,
    InquiryStatus,
)

router = APIRouter(prefix="/inquiries")
DbSession = Annotated[Session, Depends(get_db)]


def _own_inquiry_or_error(db: Session, inquiry_id: uuid.UUID, user_id: uuid.UUID) -> Inquiry:
    inquiry = db.get(Inquiry, inquiry_id)
    if inquiry is None:
        raise HTTPException(status_code=404, detail="문의를 찾을 수 없습니다")
    if inquiry.user_id != user_id:
        raise HTTPException(status_code=403, detail="다른 사용자의 문의입니다")
    return inquiry


@router.get("", response_model=InquiryListResponse, summary="내 문의 목록")
def list_inquiries(
    current_user: CurrentUser,
    db: DbSession,
    inquiry_status: Annotated[InquiryStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> InquiryListResponse:
    conditions = [Inquiry.user_id == current_user.id]
    if inquiry_status is not None:
        conditions.append(Inquiry.status == inquiry_status)

    total = db.scalar(select(func.count(Inquiry.id)).where(*conditions)) or 0
    inquiries = db.scalars(
        select(Inquiry)
        .where(*conditions)
        .order_by(desc(Inquiry.created_at))
        .limit(limit)
        .offset(offset)
    ).all()
    return InquiryListResponse(
        items=[InquiryListItem.model_validate(inquiry) for inquiry in inquiries],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    response_model=InquiryDetail,
    status_code=status.HTTP_201_CREATED,
    summary="문의 작성",
)
def create_inquiry(
    payload: InquiryCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> InquiryDetail:
    inquiry = Inquiry(
        user_id=current_user.id,
        category=payload.category,
        title=payload.title,
        content=payload.content,
        image_urls=payload.image_urls or None,
        status="pending",
    )
    db.add(inquiry)
    db.commit()
    db.refresh(inquiry)
    return InquiryDetail.model_validate(inquiry)


@router.get("/{inquiry_id}", response_model=InquiryDetail, summary="문의 상세")
def get_inquiry(
    inquiry_id: uuid.UUID, current_user: CurrentUser, db: DbSession
) -> InquiryDetail:
    inquiry = _own_inquiry_or_error(db, inquiry_id, current_user.id)
    return InquiryDetail.model_validate(inquiry)
