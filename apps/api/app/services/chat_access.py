"""대화 소유권 확인과 목록에 붙는 계산값.

`route_access.py` 와 같은 자리다 — "가져오면서 확인까지" 하는 함수를 한 곳에
모아두면 엔드포인트마다 복사하다 한 곳을 빠뜨리는 사고가 없다.

**없는 것은 404, 남의 것은 403 이다.** 전부 403 으로 합치면 남의 대화 id 를
찍어보며 존재 여부를 알아낼 수 있게 된다.
"""

import uuid
from collections.abc import Sequence
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.db.models import ChatConversation, ChatMessage, Place, User
from app.db.models.enums import MessageRole, PetPolicyType
from app.schemas.chat import ChatPlaceSummary, ConversationItem
from app.services.place_query import policy_type_expr

KST = ZoneInfo("Asia/Seoul")

#: 대화 목록 한 줄에 보이는 미리보기 길이. 설계 결정 D4
#: (docs/planning/chatbot-design-decisions.md).
PREVIEW_LENGTH = 20

#: 사용자 한 명이 가질 수 있는 대화 수. 넘으면 만들지 못한다. 설계 결정 D2 —
#: 자동으로 지우지 않는 이유는 사용자가 아껴둔 대화를 예고 없이 없애기 때문이다.
MAX_CONVERSATIONS = 100

#: 서버가 만드는 대화 제목 길이 상한 (ai-io-column-design 7.6 — 첫 질문 30자 문장 경계 절단).
TITLE_MAX_LENGTH = 30

#: 질문이 공백뿐이라 제목을 만들 수 없을 때의 폴백.
TITLE_FALLBACK = "새 대화"


def derive_title(question: str, limit: int = TITLE_MAX_LENGTH) -> str:
    """첫 질문에서 대화 제목을 만든다 — limit 자 이내, 문장 경계 우선 절단.

    LLM 을 쓰지 않는 결정적 규칙(설계 7.6): 개행·연속 공백을 하나로 정리한 뒤
    limit 이내면 그대로, 넘으면 앞 limit 자 안의 **마지막 문장부호(.?!…)**에서,
    없으면 **마지막 공백**에서 자른다. 경계가 너무 앞(절반 미만)이면 제목이
    빈약해지므로 하드 컷을 쓴다.
    """
    text = " ".join(question.split())
    if not text:
        return TITLE_FALLBACK
    if len(text) <= limit:
        return text
    head = text[:limit]
    punct = max(head.rfind(ch) for ch in ".?!…")
    if punct >= limit // 2:
        return head[: punct + 1]
    space = head.rfind(" ")
    if space >= limit // 2:
        return head[:space]
    return head


def touch_conversation(conversation: ChatConversation, when: datetime) -> None:
    """대화 목록의 정렬 기준을 방금 이야기한 시각으로 옮긴다.

    ## 왜 직접 넣나

    `updated_at` 에 `onupdate=func.now()` 가 붙어 있지만, 그건 **대화 행 자체를
    UPDATE 할 때만** 동작한다. 메시지는 `chat_messages` 에 들어가므로 대화 행은
    건드려지지 않고, 그러면 목록 정렬(`updated_at desc`)이 "최근에 이야기한 대화"가
    아니라 사실상 **첫 질문 순서**로 굳는다(제목을 지을 때 딱 한 번만 대화 행이
    바뀌기 때문이다).

    ## 왜 시각을 인자로 받나

    메시지에 넣은 시각과 **같은 값**을 써야 하기 때문이다. `func.now()` 는
    트랜잭션 시작 시각이라, 질문과 답변을 서로 다른 트랜잭션에 저장하는 지금
    구조에서는 목록의 시각이 메시지의 시각과 어긋날 수 있다(create_message 주석 참고).

    호출한 쪽이 커밋한다 — 질문·답변 저장과 같은 트랜잭션에 묶여야
    "메시지는 남았는데 목록은 안 올라온" 상태가 생기지 않는다.
    """
    conversation.updated_at = when


def load_owned_conversation(
    db: Session, conversation_id: uuid.UUID, user: User
) -> ChatConversation:
    conversation = db.get(ChatConversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="대화를 찾을 수 없습니다")
    if conversation.user_id != user.id:
        raise HTTPException(status_code=403, detail="다른 사용자의 대화입니다")
    return conversation


def message_count_expr() -> ColumnElement[int]:
    """이 대화의 메시지 개수."""
    return (
        select(func.count(ChatMessage.id))
        .where(ChatMessage.conversation_id == ChatConversation.id)
        .correlate(ChatConversation)
        .scalar_subquery()
    )


def last_message_preview_expr() -> ColumnElement[str | None]:
    """마지막 메시지 앞부분. 메시지가 없으면 NULL.

    **`system` 은 건너뛴다.** 화면에 노출하지 않기로 한 역할이라, 목록 미리보기에
    떠 있으면 사용자가 자기가 쓰지 않은 말을 보게 된다.

    자르는 일을 SQL 에 맡기는 이유는 답변 본문이 길 수 있어서다. 스무 자만
    필요한데 스무 줄을 가져올 이유가 없다.
    """
    return (
        select(func.left(ChatMessage.content, PREVIEW_LENGTH))
        .where(
            ChatMessage.conversation_id == ChatConversation.id,
            ChatMessage.role != MessageRole.SYSTEM,
        )
        .correlate(ChatConversation)
        .order_by(ChatMessage.created_at.desc())
        .limit(1)
        .scalar_subquery()
    )


def with_conversation_stats(statement: Select) -> Select:
    """대화 쿼리에 계산값 열을 붙인다.

    대화마다 따로 세면 20개짜리 목록 하나에 쿼리가 40번 나간다(N+1).
    `place_query.with_computed_columns` 와 같은 방식으로 **쿼리 한 줄에 얹는다.**
    """
    return statement.add_columns(
        last_message_preview_expr().label("last_message_preview"),
        message_count_expr().label("message_count"),
    )


def to_conversation_item(
    conversation: ChatConversation, preview: str | None, count: int
) -> ConversationItem:
    """`with_conversation_stats` 가 돌려준 행 하나를 응답으로 만든다."""
    return ConversationItem(
        id=conversation.id,
        title=conversation.title,
        route_id=conversation.route_id,
        last_message_preview=preview,
        message_count=count,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


def conversation_with_stats(db: Session, conversation_id: uuid.UUID) -> ConversationItem:
    """대화 하나를 계산값까지 채워서 돌려준다. 상세·수정 응답이 쓴다."""
    row = db.execute(
        with_conversation_stats(
            select(ChatConversation).where(ChatConversation.id == conversation_id)
        )
    ).one()
    return to_conversation_item(row[0], row.last_message_preview, row.message_count)


def asked_today(db: Session, user: User) -> int:
    """오늘 이 사용자가 보낸 질문 수. 하루 상한(설계 결정 E3)을 재는 데 쓴다.

    **KST 자정 기준**이다. 서버가 어디서 돌든 사용자가 보는 날짜로 센다.
    `func.now()` 를 쓰지 않는 이유는 그 값이 트랜잭션 시작 시각이라
    "오늘"의 기준으로는 헷갈리기 때문이다.
    """
    midnight = datetime.now(KST).replace(hour=0, minute=0, second=0, microsecond=0)
    return (
        db.scalar(
            select(func.count(ChatMessage.id))
            .join(ChatConversation, ChatConversation.id == ChatMessage.conversation_id)
            .where(
                ChatConversation.user_id == user.id,
                ChatMessage.role == MessageRole.USER,
                ChatMessage.created_at >= midnight,
            )
        )
        or 0
    )


def recent_history(db: Session, conversation_id: uuid.UUID, limit: int) -> list[ChatMessage]:
    """모델에게 함께 보낼 지난 메시지. 오래된 순으로 돌려준다.

    **최근 `limit` 개를 고른 뒤 다시 오래된 순으로 뒤집는다.** 앞에서부터
    자르면 대화 초반만 남아 정작 방금 한 이야기를 모델이 못 본다.

    `system` 은 제외한다 — 시스템 프롬프트는 매번 새로 만들어 넣는다.
    """
    newest = db.scalars(
        select(ChatMessage)
        .where(
            ChatMessage.conversation_id == conversation_id,
            ChatMessage.role != MessageRole.SYSTEM,
        )
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    ).all()
    return list(reversed(newest))


def places_of(
    db: Session, messages: Sequence[ChatMessage]
) -> dict[uuid.UUID, ChatPlaceSummary]:
    """이 페이지에 실린 메시지들이 언급한 장소를 **한 번에** 가져온다.

    `referenced_place_ids` 는 외래키가 아니라 단순 UUID 배열이라 참조 무결성이
    없다. **찾지 못한 id 는 그냥 빠진다** — 장소가 지워졌거나 비활성이면
    배열에서 사라진다고 명세에 적혀 있다(docs/api/chatbot.md).
    """
    place_ids = {
        place_id
        for message in messages
        for place_id in (message.referenced_place_ids or [])
    }
    if not place_ids:
        return {}

    rows = db.execute(
        select(Place, policy_type_expr().label("pet_policy_type")).where(
            Place.id.in_(place_ids), Place.is_active.is_(True)
        )
    ).all()

    return {
        row[0].id: ChatPlaceSummary(
            id=row[0].id,
            name=row[0].name,
            category=row[0].category,
            address=row[0].road_address or row[0].address,
            primary_image_url=row[0].primary_image_url,
            latitude=float(row[0].latitude),
            longitude=float(row[0].longitude),
            pet_policy_type=PetPolicyType(row.pet_policy_type),
        )
        for row in rows
    }
