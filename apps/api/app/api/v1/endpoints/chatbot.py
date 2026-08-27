"""AI 챗봇 대화·메시지 엔드포인트.

명세(docs/api/chatbot.md)의 엔드포인트 7개가 전부 여기 있다.

## 마지막 하나는 명세와 전달 방식이 다르다

`POST /chat/conversations/{id}/messages` 는 명세상 SSE 스트림이지만
(`start` → `delta` → `done`), 지금은 **JSON 한 번에** 돌려준다. 앱에서 먼저
눌러볼 수 있게 하기 위해서다. 도구 호출·프롬프트·저장은 두 방식이 같아서
스트리밍으로 옮길 때 전달 방식만 바뀐다. 중지 버튼도 그때 함께 붙인다.

## LLM 은 이 파일에 없다

OpenAI 호출과 도구 루프는 `app/integrations/llm/chat.py` 에 있다.
여기서는 `generate_answer()` 하나만 부른다 — 벤더를 바꿔도 이 파일은 안 바뀐다.
"""

import uuid
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.core.config import settings
from app.db.models import ChatConversation, ChatMessage
from app.db.models.enums import MessageRole
from app.db.session import get_db
from app.integrations.llm.chat import (
    HISTORY_LIMIT,
    ChatGenerationError,
    ChatTimeoutError,
    generate_answer,
    to_history,
)
from app.schemas.chat import (
    AnswerResponse,
    ChatPlaceSummary,
    ConversationCreate,
    ConversationCreated,
    ConversationItem,
    ConversationListResponse,
    ConversationUpdate,
    MessageCreate,
    MessageItem,
    MessageListResponse,
)
from app.services.chat_access import (
    KST,
    MAX_CONVERSATIONS,
    asked_today,
    conversation_with_stats,
    load_owned_conversation,
    places_of,
    recent_history,
    to_conversation_item,
    with_conversation_stats,
)
from app.services.route_access import load_owned_route

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]


def _to_message_item(
    message: ChatMessage, summaries: dict[uuid.UUID, ChatPlaceSummary]
) -> MessageItem:
    """메시지 한 건을 응답으로. 목록과 질문 전송이 함께 쓴다.

    `referenced_place_ids` 에 있어도 `summaries` 에 없으면 **뺀다** — 장소가
    지워졌거나 비활성이면 배열에서 사라진다고 명세에 적혀 있다.
    """
    return MessageItem(
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
        items=[_to_message_item(message, summaries) for message in messages],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/chat/conversations/{conversation_id}/messages",
    response_model=AnswerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="질문 전송",
)
def create_message(
    conversation_id: uuid.UUID,
    payload: MessageCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> AnswerResponse:
    """질문을 보내고 답변을 받는다. **두 행이 저장된다** — 질문과 답변.

    ## 명세와 다른 점: JSON 이다

    docs/api/chatbot.md 는 이 엔드포인트만 SSE 스트림으로 정해뒀다
    (`start` → `delta` → `done`). 지금은 **JSON 한 번에** 돌려준다. 앱에서 먼저
    눌러볼 수 있게 하기 위해서고, 도구 호출·프롬프트·저장은 두 방식이 같아서
    스트리밍으로 옮길 때 **전달 방식만** 바뀐다.

    ## 실패하면 질문도 저장하지 않는다

    명세의 SSE 는 질문을 먼저 저장하고(`start`) 답변이 끊기면 질문만 남긴다 —
    앱이 재시도 버튼을 띄우면 되기 때문이다. JSON 은 그럴 중간 지점이 없다.
    **한 번에 성공하거나 아무것도 남기지 않는다.** 실패한 질문만 쌓이면 다음
    질문의 맥락이 어긋난다.
    """
    load_owned_conversation(db, conversation_id, current_user)

    # 개발·시연 중에 막히면 곤란해서 local 에서는 세지 않는다(설계 결정 E3).
    if settings.environment != "local":
        if asked_today(db, current_user) >= settings.chat_daily_limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="오늘 질문 가능한 횟수를 다 쓰셨어요. 내일 다시 이용해 주세요",
            )

    history = [
        to_history(message.role, message.content)
        for message in recent_history(db, conversation_id, HISTORY_LIMIT)
    ]

    # 두 메시지의 시각을 **직접** 넣는다. 그냥 두면 컬럼 기본값인 now() 가 쓰이는데,
    # PostgreSQL 의 now() 는 **트랜잭션 시작 시각**이라 같은 트랜잭션에서 저장하는
    # 질문과 답변이 **똑같은 created_at** 을 받는다. 그러면 정렬 기준이 없어져
    # 채팅 화면에서 답변이 질문보다 위에 뜨고, 다음 질문 때 모델에게 가는 맥락
    # 순서도 뒤집힌다. 대화 목록처럼 id 로 동점 처리할 수도 없다 — 무작위 UUID 라
    # 시간 순서를 담고 있지 않다.
    asked_at = datetime.now(KST)

    try:
        answer = generate_answer(db, history, payload.content)
    except ChatTimeoutError as error:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="답변이 늦어지고 있어요. 다시 시도해 주세요",
        ) from error
    except ChatGenerationError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="답변 생성에 실패했어요. 다시 시도해 주세요",
        ) from error

    # 답변 생성에 걸린 시간이 있어 보통은 자연히 뒤가 되지만, 가짜 구현이나
    # 캐시로 즉시 돌아오는 경우까지 생각해 **반드시 뒤**가 되게 못박는다.
    answered_at = max(datetime.now(KST), asked_at + timedelta(milliseconds=1))

    question = ChatMessage(
        conversation_id=conversation_id,
        role=MessageRole.USER,
        content=payload.content,
        created_at=asked_at,
    )
    db.add(question)
    db.flush()

    reply = ChatMessage(
        conversation_id=conversation_id,
        role=MessageRole.ASSISTANT,
        content=answer.content,
        referenced_place_ids=answer.referenced_place_ids or None,
        model_name=answer.model_name,
        created_at=answered_at,
    )
    db.add(reply)
    db.commit()
    db.refresh(question)
    db.refresh(reply)

    summaries = places_of(db, [reply])
    return AnswerResponse(
        user_message=_to_message_item(question, {}),
        assistant_message=_to_message_item(reply, summaries),
    )
