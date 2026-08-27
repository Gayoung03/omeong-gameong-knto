"""AI 챗봇 대화·메시지 엔드포인트.

명세(docs/api/chatbot.md)의 엔드포인트 7개 중 **6개**가 여기 있다.
빠진 하나는 질문을 보내고 답변을 받는 `POST /chat/conversations/{id}/messages` 로,
그것만 JSON 이 아니라 SSE 스트림이고 LLM·장소 검색이 있어야 동작한다.

그래서 지금 이 파일에는 **LLM 호출이 한 줄도 없다.** 대화를 만들고, 목록을 주고,
지우는 일만 한다. 검색 도구(지역·카테고리 어휘 확정 대기)와 무관하게 먼저 만들 수
있는 부분이라 떼어냈다.

## 메시지는 아직 이 API 로 생기지 않는다

`chat_messages` 행은 스트리밍 엔드포인트가 만든다. 그때까지 메시지 목록은
비어 있고, `messageCount` 는 0, `lastMessagePreview` 는 null 이다. 조회 쪽을 미리
맞춰두는 이유는 앱이 대화 목록·상세 화면을 먼저 붙일 수 있게 하기 위해서다.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.db.models import ChatConversation, ChatMessage
from app.db.session import get_db
from app.schemas.chat import (
    ConversationCreate,
    ConversationCreated,
    ConversationItem,
    ConversationListResponse,
    ConversationUpdate,
    MessageItem,
    MessageListResponse,
)
from app.services.chat_access import (
    MAX_CONVERSATIONS,
    conversation_with_stats,
    load_owned_conversation,
    places_of,
    to_conversation_item,
    with_conversation_stats,
)
from app.services.route_access import load_owned_route

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]


@router.get("/chat/conversations", response_model=ConversationListResponse, summary="대화 목록")
def list_conversations(
    current_user: CurrentUser,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ConversationListResponse:
    """최근에 이야기한 대화부터 준다.

    `chat_conversations` 에 `(user_id, updated_at)` 인덱스가 있어 이 정렬이 싸다.
    """
    condition = ChatConversation.user_id == current_user.id
    total = db.scalar(select(func.count(ChatConversation.id)).where(condition)) or 0

    rows = db.execute(
        with_conversation_stats(select(ChatConversation).where(condition))
        # id 는 동점 처리용이다. 같은 순간에 갱신된 대화가 둘이면 정렬 순서가
        # 매번 달라지고, 그러면 페이지를 넘길 때 어떤 대화는 두 번 나오고
        # 어떤 대화는 아예 안 나온다.
        .order_by(ChatConversation.updated_at.desc(), ChatConversation.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()

    return ConversationListResponse(
        items=[
            to_conversation_item(row[0], row.last_message_preview, row.message_count)
            for row in rows
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/chat/conversations",
    response_model=ConversationCreated,
    status_code=status.HTTP_201_CREATED,
    summary="대화 시작",
)
def create_conversation(
    payload: ConversationCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> ConversationCreated:
    """빈 대화를 하나 만든다.

    **앱은 챗봇 탭을 열 때가 아니라 첫 질문을 보낼 때 이걸 부른다.** 탭을 열 때마다
    만들면 질문도 없는 빈 대화가 쌓여 아래 상한에 금방 닿는다
    (docs/planning/chatbot-design-decisions.md).

    `routeId` 를 보내면 그 여행이 **내 것인지 확인한다.** 외래키만으로는
    "존재하는 여행"까지만 보장되고 "내 여행"인지는 모른다.
    """
    if payload.route_id is not None:
        load_owned_route(db, payload.route_id, current_user)

    owned = db.scalar(
        select(func.count(ChatConversation.id)).where(
            ChatConversation.user_id == current_user.id
        )
    )
    if (owned or 0) >= MAX_CONVERSATIONS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"대화는 {MAX_CONVERSATIONS}개까지 만들 수 있어요. 안 쓰는 대화를 지워주세요",
        )

    conversation = ChatConversation(
        user_id=current_user.id,
        route_id=payload.route_id,
        title=payload.title,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return ConversationCreated.model_validate(conversation)


@router.get(
    "/chat/conversations/{conversation_id}",
    response_model=ConversationItem,
    summary="대화 상세",
)
def get_conversation(
    conversation_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> ConversationItem:
    """**메시지는 포함하지 않는다.**

    개수가 많을 수 있어 페이지네이션이 필요해서다. 대화 화면은 이 요청과
    메시지 목록을 함께 부른다. 제목만 필요할 때(목록을 거치지 않고 바로 들어올 때)는
    이 요청 하나로 끝난다.
    """
    load_owned_conversation(db, conversation_id, current_user)
    return conversation_with_stats(db, conversation_id)


@router.patch(
    "/chat/conversations/{conversation_id}",
    response_model=ConversationItem,
    summary="대화 제목 수정",
)
def update_conversation(
    conversation_id: uuid.UUID,
    payload: ConversationUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> ConversationItem:
    conversation = load_owned_conversation(db, conversation_id, current_user)
    conversation.title = payload.title
    db.commit()
    return conversation_with_stats(db, conversation_id)


@router.delete(
    "/chat/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="대화 삭제",
)
def delete_conversation(
    conversation_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> Response:
    """물리 삭제다. `chat_messages` 도 `ON DELETE CASCADE` 로 함께 지워진다."""
    conversation = load_owned_conversation(db, conversation_id, current_user)
    db.delete(conversation)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/chat/conversations/{conversation_id}/messages",
    response_model=MessageListResponse,
    summary="메시지 목록",
)
def list_messages(
    conversation_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> MessageListResponse:
    """**오래된 순**으로 준다.

    채팅 화면이 위에서 아래로 읽히기 때문에 다른 목록과 정렬이 반대다.
    """
    load_owned_conversation(db, conversation_id, current_user)

    condition = ChatMessage.conversation_id == conversation_id
    total = db.scalar(select(func.count(ChatMessage.id)).where(condition)) or 0

    messages = db.scalars(
        select(ChatMessage)
        .where(condition)
        .order_by(ChatMessage.created_at)
        .limit(limit)
        .offset(offset)
    ).all()

    summaries = places_of(db, messages)

    return MessageListResponse(
        items=[
            MessageItem(
                id=message.id,
                conversation_id=message.conversation_id,
                role=message.role,
                content=message.content,
                referenced_places=[
                    summaries[place_id]
                    for place_id in (message.referenced_place_ids or [])
                    if place_id in summaries
                ],
                model_name=message.model_name,
                created_at=message.created_at,
            )
            for message in messages
        ],
        total=total,
        limit=limit,
        offset=offset,
    )
