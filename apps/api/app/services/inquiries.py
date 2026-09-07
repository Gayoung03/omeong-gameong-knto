"""1:1 문의 관리자 답변.

답변을 달면 상태가 `completed` 로 바뀌고(DB CHECK `completed_has_answer`),
문의자에게 `inquiry_answered` 알림을 보낸다 — 단, 알림을 끈 사용자는 제외한다.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.db.models import AdminInquiryAuditLog, Inquiry
from app.services.notifications import add_notification, send_pushes

#: 화면에 보일 한글 라벨. API/DB 는 영문 코드로 통일한다(docs/api/notifications.md).
INQUIRY_CATEGORY_LABELS: dict[str, str] = {
    "account": "계정 및 회원정보",
    "pet": "반려동물 정보",
    "saved": "저장한 장소·코스",
    "schedule": "여행 일정",
    "bug": "오류·불편",
    "etc": "기타",
}


def category_label(code: str) -> str:
    return INQUIRY_CATEGORY_LABELS.get(code, code)


#: 답변 꼬릿말 기본값. 관리자가 화면에서 고쳐도 된다 — 저장은 관리자가 보낸 그대로.
INQUIRY_ANSWER_FOOTER = "감사합니다.\n오멍가멍 드림"


def answer_header(asker_nickname: str) -> str:
    """문의자 이름을 넣은 인사말."""
    name = (asker_nickname or "").strip() or "고객"
    return f"{name}님, 안녕하세요.\n오멍가멍입니다."


def answer_template(asker_nickname: str) -> str:
    """답변 편집기의 초기값. 머릿말 + 빈 본문 + 꼬릿말. 관리자가 자유롭게 수정한다."""
    return f"{answer_header(asker_nickname)}\n\n\n\n{INQUIRY_ANSWER_FOOTER}"


def answer_inquiry(
    db: Session, inquiry: Inquiry, *, answer: str, actor_id: uuid.UUID
) -> Inquiry:
    """관리자가 작성한 답변 **전체**를 그대로 저장하고 문의자에게 알림을 보낸다.

    머릿말·꼬릿말은 편집기 초기값으로만 제공하고, 저장은 보낸 그대로 한다.
    호출 측이 완료 상태를 미리 막는다(409).
    """
    full_answer = answer.strip()
    inquiry.answer = full_answer
    inquiry.answered_at = datetime.now(UTC)
    inquiry.status = "completed"
    db.add(
        AdminInquiryAuditLog(
            inquiry_id=inquiry.id,
            actor_user_id=actor_id,
            action="answered",
            previous_status="pending",
            next_status="completed",
            changes={"answer": {"after": full_answer[:200]}},
        )
    )
    db.commit()
    db.refresh(inquiry)

    # 기본값이 True 라 None 도 "받겠다"로 본다. 명시적으로 False 인 사람만 제외한다.
    if inquiry.asker.inquiry_answer_notification_enabled is not False:
        notification = add_notification(
            db,
            user_id=inquiry.user_id,
            type="inquiry_answered",
            target_id=inquiry.id,
            title="문의에 답변이 등록되었습니다",
            content=f"'{category_label(inquiry.category)}' 문의에 답변이 달렸어요.",
        )
        db.commit()
        send_pushes(db, notification)

    return inquiry
