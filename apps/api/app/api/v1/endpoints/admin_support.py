"""관리자 고객지원 콘솔 API — 1:1 문의 답변, 공지사항 관리.

모든 엔드포인트는 ``CurrentAdmin`` 을 요구한다. 패턴은 ``admin.py`` (여행 이야기)를
그대로 따른다 — row lock, 409 상태 전이, 도메인별 감사 로그.
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import CurrentAdmin
from app.core.config import settings
from app.db.models import AdminInquiryAuditLog, AdminNoticeAuditLog, Inquiry, Notice
from app.db.session import get_db
from app.schemas.admin_inquiry import (
    AdminInquiryAnswerRequest,
    AdminInquiryAsker,
    AdminInquiryAuditResponse,
    AdminInquiryDetail,
    AdminInquiryDraftResponse,
    AdminInquiryListItem,
    AdminInquiryListResponse,
    AdminInquiryOrder,
    AdminInquirySort,
)
from app.schemas.admin_notice import (
    AdminNoticeAuditResponse,
    AdminNoticeCreate,
    AdminNoticeDetail,
    AdminNoticeFilter,
    AdminNoticeListItem,
    AdminNoticeListResponse,
    AdminNoticePublishRequest,
    AdminNoticeUpdate,
)
from app.schemas.inquiry import InquiryCategory, InquiryStatus
from app.services import inquiries as inquiry_service
from app.services import inquiry_drafting
from app.services import notices as notice_service
from app.services.admin_audit import json_value

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin")
DbSession = Annotated[Session, Depends(get_db)]


# ---------------------------------------------------------------------------
# 1:1 문의
# ---------------------------------------------------------------------------


def _inquiry_or_404(db: Session, inquiry_id: uuid.UUID, *, lock: bool = False) -> Inquiry:
    query = select(Inquiry).where(Inquiry.id == inquiry_id)
    if lock:
        query = query.with_for_update()
    inquiry = db.scalar(query)
    if inquiry is None:
        raise HTTPException(status_code=404, detail="문의를 찾을 수 없습니다")
    return inquiry


def _inquiry_detail(db: Session, inquiry: Inquiry) -> AdminInquiryDetail:
    audit_logs = db.scalars(
        select(AdminInquiryAuditLog)
        .where(AdminInquiryAuditLog.inquiry_id == inquiry.id)
        .order_by(AdminInquiryAuditLog.created_at.desc())
        .limit(30)
    ).all()
    return AdminInquiryDetail(
        id=inquiry.id,
        category=inquiry.category,
        status=inquiry.status,
        title=inquiry.title,
        content=inquiry.content,
        image_urls=inquiry.image_urls,
        answer=inquiry.answer,
        answered_at=inquiry.answered_at,
        answer_template=inquiry_service.answer_template(inquiry.asker.nickname),
        asker=AdminInquiryAsker.model_validate(inquiry.asker),
        created_at=inquiry.created_at,
        updated_at=inquiry.updated_at,
        audit_logs=[AdminInquiryAuditResponse.model_validate(log) for log in audit_logs],
    )


@router.get(
    "/inquiries", response_model=AdminInquiryListResponse, summary="관리자 문의 목록"
)
def list_admin_inquiries(
    db: DbSession,
    _current_admin: CurrentAdmin,
    inquiry_status: Annotated[InquiryStatus | None, Query(alias="status")] = None,
    category: InquiryCategory | None = None,
    search: Annotated[str | None, Query(max_length=200)] = None,
    sort_by: Annotated[AdminInquirySort, Query(alias="sortBy")] = "created_at",
    order: AdminInquiryOrder = "desc",
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
) -> AdminInquiryListResponse:
    conditions = []
    if inquiry_status is not None:
        conditions.append(Inquiry.status == inquiry_status)
    if category is not None:
        conditions.append(Inquiry.category == category)
    if search and search.strip():
        conditions.append(Inquiry.title.ilike(f"%{search.strip()}%"))

    total = db.scalar(select(func.count(Inquiry.id)).where(*conditions)) or 0
    sort_column = Inquiry.answered_at if sort_by == "answered_at" else Inquiry.created_at
    direction = desc if order == "desc" else asc
    inquiries = db.scalars(
        select(Inquiry)
        .where(*conditions)
        .options(selectinload(Inquiry.asker))
        .order_by(direction(sort_column).nulls_last(), Inquiry.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()

    return AdminInquiryListResponse(
        items=[
            AdminInquiryListItem(
                id=inquiry.id,
                category=inquiry.category,
                status=inquiry.status,
                title=inquiry.title,
                asker_nickname=inquiry.asker.nickname,
                created_at=inquiry.created_at,
                answered_at=inquiry.answered_at,
            )
            for inquiry in inquiries
        ],
        total=total,
        page=page,
        limit=limit,
    )


@router.get(
    "/inquiries/{inquiry_id}",
    response_model=AdminInquiryDetail,
    summary="관리자 문의 상세",
)
def get_admin_inquiry(
    inquiry_id: uuid.UUID, db: DbSession, _current_admin: CurrentAdmin
) -> AdminInquiryDetail:
    return _inquiry_detail(db, _inquiry_or_404(db, inquiry_id))


@router.post(
    "/inquiries/{inquiry_id}/answer",
    response_model=AdminInquiryDetail,
    summary="문의 답변 등록",
)
def answer_admin_inquiry(
    inquiry_id: uuid.UUID,
    payload: AdminInquiryAnswerRequest,
    db: DbSession,
    current_admin: CurrentAdmin,
) -> AdminInquiryDetail:
    inquiry = _inquiry_or_404(db, inquiry_id, lock=True)
    if inquiry.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 답변이 등록된 문의입니다",
        )
    inquiry_service.answer_inquiry(
        db, inquiry, answer=payload.answer, actor_id=current_admin.id
    )
    return _inquiry_detail(db, inquiry)


@router.post(
    "/inquiries/{inquiry_id}/draft-answer",
    response_model=AdminInquiryDraftResponse,
    summary="문의 답변 AI 초안",
)
def draft_admin_inquiry_answer(
    inquiry_id: uuid.UUID, db: DbSession, current_admin: CurrentAdmin
) -> AdminInquiryDraftResponse:
    inquiry = _inquiry_or_404(db, inquiry_id)
    if inquiry.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 답변이 등록된 문의입니다",
        )
    # 토큰 절약 — 하루 한도. local 에서는 세지 않는다(chat_daily_limit 과 같은 방식).
    if settings.environment != "local":
        used = inquiry_service.ai_drafts_today(db, current_admin.id)
        if used >= settings.inquiry_draft_daily_limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="오늘 AI 초안 생성 한도를 다 썼어요. 내일 다시 시도해 주세요.",
            )
    try:
        draft = inquiry_drafting.draft_answer(db, inquiry)
    except RuntimeError as error:
        # OPENAI_API_KEY 미설정 등 설정 문제.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI 초안 기능이 설정되지 않았어요",
        ) from error
    except Exception as error:  # noqa: BLE001 - 외부 LLM 호출 실패는 전부 502 로 요약
        logger.exception("문의 답변 초안 생성 실패", extra={"inquiry_id": str(inquiry_id)})
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI 초안 생성에 실패했어요. 잠시 후 다시 시도해 주세요.",
        ) from error

    # 성공한 호출만 한도에 센다. 감사 로그로 남겨 재시작해도 유지된다.
    inquiry_service.record_ai_draft(db, inquiry, current_admin.id)
    db.commit()
    return AdminInquiryDraftResponse(
        reply=draft.reply,
        used_context=draft.used_context,
        needs_human_review=draft.needs_human_review,
        model=draft.model,
    )


# ---------------------------------------------------------------------------
# 공지사항
# ---------------------------------------------------------------------------

_NOTICE_EDITABLE_FIELDS = ("title", "content", "is_pinned", "is_active", "published_at")


def _notice_or_404(db: Session, notice_id: uuid.UUID, *, lock: bool = False) -> Notice:
    query = select(Notice).where(Notice.id == notice_id)
    if lock:
        query = query.with_for_update()
    notice = db.scalar(query)
    if notice is None:
        raise HTTPException(status_code=404, detail="공지사항을 찾을 수 없습니다")
    return notice


def _notice_audit(
    db: Session,
    *,
    notice: Notice,
    actor_id: uuid.UUID,
    action: str,
    previous_status: str | None = None,
    next_status: str | None = None,
    changes: dict | None = None,
) -> None:
    db.add(
        AdminNoticeAuditLog(
            notice_id=notice.id,
            actor_user_id=actor_id,
            action=action,
            previous_status=previous_status,
            next_status=next_status,
            changes=changes or {},
        )
    )


def _notice_detail(db: Session, notice: Notice) -> AdminNoticeDetail:
    audit_logs = db.scalars(
        select(AdminNoticeAuditLog)
        .where(AdminNoticeAuditLog.notice_id == notice.id)
        .order_by(AdminNoticeAuditLog.created_at.desc())
        .limit(30)
    ).all()
    return AdminNoticeDetail(
        id=notice.id,
        title=notice.title,
        content=notice.content,
        is_pinned=notice.is_pinned,
        is_active=notice.is_active,
        published_at=notice.published_at,
        announced_at=notice.announced_at,
        created_at=notice.created_at,
        updated_at=notice.updated_at,
        audit_logs=[AdminNoticeAuditResponse.model_validate(log) for log in audit_logs],
    )


@router.get("/notices", response_model=AdminNoticeListResponse, summary="관리자 공지 목록")
def list_admin_notices(
    db: DbSession,
    _current_admin: CurrentAdmin,
    notice_filter: Annotated[AdminNoticeFilter, Query(alias="filter")] = "all",
    search: Annotated[str | None, Query(max_length=200)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
) -> AdminNoticeListResponse:
    conditions = []
    if notice_filter == "announced":
        conditions.append(Notice.announced_at.is_not(None))
    elif notice_filter == "draft":
        conditions.append(Notice.announced_at.is_(None))
    if search and search.strip():
        conditions.append(Notice.title.ilike(f"%{search.strip()}%"))

    total = db.scalar(select(func.count(Notice.id)).where(*conditions)) or 0
    notices = db.scalars(
        select(Notice)
        .where(*conditions)
        .order_by(desc(Notice.published_at), desc(Notice.created_at))
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()
    return AdminNoticeListResponse(
        items=[AdminNoticeListItem.model_validate(notice) for notice in notices],
        total=total,
        page=page,
        limit=limit,
    )


@router.get(
    "/notices/{notice_id}", response_model=AdminNoticeDetail, summary="관리자 공지 상세"
)
def get_admin_notice(
    notice_id: uuid.UUID, db: DbSession, _current_admin: CurrentAdmin
) -> AdminNoticeDetail:
    return _notice_detail(db, _notice_or_404(db, notice_id))


@router.post(
    "/notices",
    response_model=AdminNoticeDetail,
    status_code=status.HTTP_201_CREATED,
    summary="공지 초안 생성",
)
def create_admin_notice(
    payload: AdminNoticeCreate, db: DbSession, current_admin: CurrentAdmin
) -> AdminNoticeDetail:
    notice = Notice(
        title=payload.title,
        content=payload.content,
        is_pinned=payload.is_pinned,
        is_active=False,
        published_at=payload.published_at or datetime.now(UTC),
    )
    db.add(notice)
    db.flush()
    _notice_audit(
        db,
        notice=notice,
        actor_id=current_admin.id,
        action="created",
        next_status="draft",
    )
    db.commit()
    db.refresh(notice)
    return _notice_detail(db, notice)


@router.patch(
    "/notices/{notice_id}", response_model=AdminNoticeDetail, summary="공지 수정"
)
def update_admin_notice(
    notice_id: uuid.UUID,
    payload: AdminNoticeUpdate,
    db: DbSession,
    current_admin: CurrentAdmin,
) -> AdminNoticeDetail:
    notice = _notice_or_404(db, notice_id, lock=True)
    values = payload.model_dump(exclude_unset=True)
    json_values = payload.model_dump(exclude_unset=True, mode="json")

    changes: dict[str, dict[str, object]] = {}
    for field in _NOTICE_EDITABLE_FIELDS:
        if field not in values:
            continue
        before = getattr(notice, field)
        after = values[field]
        if before == after:
            continue
        changes[field] = {"before": json_value(before), "after": json_values[field]}
        setattr(notice, field, after)

    if changes:
        _notice_audit(
            db,
            notice=notice,
            actor_id=current_admin.id,
            action="updated",
            changes=changes,
        )
        db.commit()
        db.refresh(notice)
    return _notice_detail(db, notice)


@router.post(
    "/notices/{notice_id}/publish",
    response_model=AdminNoticeDetail,
    summary="공지 발행 (전 사용자 알림)",
)
def publish_admin_notice(
    notice_id: uuid.UUID,
    payload: AdminNoticePublishRequest,
    db: DbSession,
    current_admin: CurrentAdmin,
) -> AdminNoticeDetail:
    notice = _notice_or_404(db, notice_id, lock=True)
    if notice.announced_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 발송된 공지입니다. 다시 보이려면 수정에서 활성화하세요.",
        )
    notice.is_active = True
    notice.published_at = payload.published_at or notice.published_at or datetime.now(UTC)
    db.flush()
    notice_service.announce_notice(db, notice)
    _notice_audit(
        db,
        notice=notice,
        actor_id=current_admin.id,
        action="published",
        previous_status="draft",
        next_status="announced",
        changes={"published_at": {"after": json_value(notice.published_at)}},
    )
    db.commit()
    db.refresh(notice)
    return _notice_detail(db, notice)


@router.post(
    "/notices/{notice_id}/unpublish",
    response_model=AdminNoticeDetail,
    summary="공지 게시 중단",
)
def unpublish_admin_notice(
    notice_id: uuid.UUID, db: DbSession, current_admin: CurrentAdmin
) -> AdminNoticeDetail:
    notice = _notice_or_404(db, notice_id, lock=True)
    if not notice.is_active:
        return _notice_detail(db, notice)
    notice.is_active = False
    _notice_audit(
        db,
        notice=notice,
        actor_id=current_admin.id,
        action="unpublished",
        changes={"is_active": {"before": True, "after": False}},
    )
    db.commit()
    db.refresh(notice)
    return _notice_detail(db, notice)
