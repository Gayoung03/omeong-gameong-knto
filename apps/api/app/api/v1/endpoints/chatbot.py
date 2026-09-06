"""AI 챗봇 대화·메시지 엔드포인트.

명세(docs/api/chatbot.md)의 엔드포인트 7개가 전부 여기 있다.

## 마지막 하나만 SSE 다

`POST /chat/conversations/{id}/messages` 는 `text/event-stream` 으로
`start` → `delta`(여러 번) → `done`(또는 실패 시 `error`) 순서로 내려준다.
스트림이 **시작되기 전** 실패(소유권 없음·사용량 초과 등)는 지금처럼 일반
JSON 에러 응답이다 — 제너레이터에 들어가기 전에 걸러지기 때문이다.

## 중지 = 연결 끊김

앱이 중지 버튼을 누르면 연결을 끊는 것 말고 다른 신호를 보내지 않는다. 서버는
"사용자가 중지했다"와 "네트워크가 끊겼다"를 구분하지 않고 **똑같이 처리** —
그때까지 만든 답변은 저장하지 않는다(질문은 이미 `start` 시점에 저장돼 있다).

## LLM 은 이 파일에 없다

OpenAI 호출과 도구 루프는 `app/integrations/llm/chat.py` 에 있다.
여기서는 `stream_answer()` 하나만 부른다 — 벤더를 바꿔도 이 파일은 안 바뀐다.
"""

import json
import uuid
from collections.abc import Generator
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.core.config import settings
from app.db.models import ChatConversation, ChatMessage
from app.db.models.enums import MessageRole
from app.db.session import get_db
from app.integrations.llm.chat import (
    HISTORY_LIMIT,
    Answer,
    ChatGenerationError,
    ChatTimeoutError,
    stream_answer,
    to_history,
)
from app.schemas.chat import (
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
    derive_title,
    load_owned_conversation,
    owned_conversations,
    places_of,
    recent_history,
    set_deleted,
    to_conversation_item,
    touch_conversation,
    with_conversation_stats,
)
from app.services.notifications import add_notification, send_pushes
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
    deleted: Annotated[bool, Query()] = False,
) -> ConversationListResponse:
    """최근에 이야기한 대화부터 준다.

    `chat_conversations` 에 `(user_id, updated_at) WHERE deleted_at IS NULL` 부분
    인덱스가 있어 이 정렬이 싸다.

    `deleted=true` 면 **휴지통**이다. 지운 대화를 지운 순서로 준다 — 방금 잘못 지운
    것이 맨 위에 있어야 되돌리기 쉽다. 같은 스키마를 쓰므로 앱은 목록 화면 코드를
    그대로 재사용할 수 있다.
    """
    condition = owned_conversations(current_user, deleted=deleted)
    total = db.scalar(select(func.count(ChatConversation.id)).where(condition)) or 0

    # id 는 동점 처리용이다. 같은 순간에 갱신된 대화가 둘이면 정렬 순서가
    # 매번 달라지고, 그러면 페이지를 넘길 때 어떤 대화는 두 번 나오고
    # 어떤 대화는 아예 안 나온다.
    newest_first = (
        ChatConversation.deleted_at.desc() if deleted else ChatConversation.updated_at.desc()
    )

    rows = db.execute(
        with_conversation_stats(select(ChatConversation).where(condition))
        .order_by(newest_first, ChatConversation.id.desc())
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

    # **살아 있는 대화만** 센다. 지운 것까지 세면 "안 쓰는 대화를 지워주세요"라고
    # 안내해 놓고 지워도 자리가 안 나는 상태가 된다.
    owned = db.scalar(
        select(func.count(ChatConversation.id)).where(owned_conversations(current_user))
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
    """**목록에서만 사라진다.** `chat_messages` 는 한 행도 지우지 않는다.

    사용자가 대화를 지우는 것은 "안 보이게 해달라"는 뜻이지 "기록을 없애달라"는
    뜻이 아니다. 그래서 `deleted_at` 만 채우고, 휴지통에서 되살릴 수 있게 둔다.

    이미 지운 대화를 또 지우면 404 다 — `load_owned_conversation` 이 걸러낸다.
    """
    conversation = load_owned_conversation(db, conversation_id, current_user)
    set_deleted(conversation, datetime.now(KST))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/chat/conversations/{conversation_id}/restore",
    response_model=ConversationItem,
    summary="대화 복구",
)
def restore_conversation(
    conversation_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> ConversationItem:
    """휴지통에서 되살린다.

    **`updated_at` 은 건드리지 않는다.** 갱신하면 복구한 대화가 목록 맨 위로 튀어
    오르는데, 되살렸을 때 기대하는 것은 "원래 있던 자리로 돌아오는 것"이다.

    지운 사이에 대화를 100개까지 새로 만들었다면 되살릴 자리가 없다. 조용히 상한을
    넘기지 않고 409 로 알린다 — 생성 거부와 같은 규칙이다.
    """
    conversation = load_owned_conversation(
        db, conversation_id, current_user, include_deleted=True
    )
    if conversation.deleted_at is None:
        raise HTTPException(status_code=404, detail="휴지통에 없는 대화입니다")

    alive = db.scalar(
        select(func.count(ChatConversation.id)).where(owned_conversations(current_user))
    )
    if (alive or 0) >= MAX_CONVERSATIONS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"대화는 {MAX_CONVERSATIONS}개까지 가질 수 있어요. 안 쓰는 대화를 지워주세요",
        )

    set_deleted(conversation, None)
    db.commit()
    return conversation_with_stats(db, conversation_id)


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


def _sse_event(payload: dict) -> str:
    r"""SSE 한 덩어리로 만든다. `\n\n` 로 끝나야 클라이언트가 이벤트 경계를 안다."""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post(
    "/chat/conversations/{conversation_id}/messages",
    summary="질문 전송 (SSE)",
)
def create_message(
    conversation_id: uuid.UUID,
    payload: MessageCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> StreamingResponse:
    """질문을 보내고 답변을 SSE 로 받는다.

    `start`(저장된 사용자 메시지) → `delta`(답변 조각, 여러 번) → `done`(저장된
    답변 메시지) 순서다. 실패하면 `done` 대신 `error` 가 온다.

    ## 질문은 스트림을 열기 전에 이미 저장한다

    `start` 를 보내는 시점에 사용자 메시지가 DB 에 있어야 하고, 스트림이 중간에
    끊겨도(중지 버튼·네트워크 문제 — 서버는 둘을 구분하지 않는다) 이 메시지는
    남아야 한다(docs/api/chatbot.md). **답변은 끝까지 갔을 때만 저장한다** —
    끊기면 저장하지 않는다.
    """
    conversation = load_owned_conversation(db, conversation_id, current_user)

    # 개발·시연 중에 막히면 곤란해서 local 에서는 세지 않는다(설계 결정 E3).
    if settings.environment != "local":
        if asked_today(db, current_user) >= settings.chat_daily_limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="오늘 질문 가능한 횟수를 다 쓰셨어요. 내일 다시 이용해 주세요",
            )

    past_messages = recent_history(db, conversation_id, HISTORY_LIMIT)
    history = [to_history(message.role, message.content) for message in past_messages]

    # 제목 없는 대화의 첫 질문이면 서버가 제목을 만든다(chatbot.md — "없으면 서버가
    # 첫 질문에서 생성"). 질문과 같은 트랜잭션이라 start 시점엔 항상 함께 저장돼 있다.
    if conversation.title is None and not past_messages:
        conversation.title = derive_title(payload.content)

    # 답변보다 먼저 저장해 스트림이 끊겨도 남긴다. 시각도 여기서 직접 넣는다 —
    # 그냥 두면 컬럼 기본값 now() 가 **트랜잭션 시작 시각**이라, 나중에 답변을
    # 별도 트랜잭션(커밋)으로 저장해도 두 메시지의 순서가 시각만으로는 보장되지
    # 않는다.
    asked_at = datetime.now(KST)
    question = ChatMessage(
        conversation_id=conversation_id,
        role=MessageRole.USER,
        content=payload.content,
        created_at=asked_at,
    )
    db.add(question)
    # 질문과 **같은 트랜잭션**에서 목록 순서를 올린다. 나눠 커밋하면 답변이 끊긴
    # 대화가 목록 아래에 남아, 사용자가 방금 물어본 대화를 못 찾는다.
    touch_conversation(conversation, asked_at)
    db.commit()
    db.refresh(question)

    def event_stream() -> Generator[str, None, None]:
        yield _sse_event(
            {
                "event": "start",
                "userMessage": _to_message_item(question, {}).model_dump(
                    mode="json", by_alias=True
                ),
            }
        )

        answer: Answer | None = None
        try:
            for piece in stream_answer(db, history, payload.content):
                if isinstance(piece, Answer):
                    answer = piece
                    break
                yield _sse_event({"event": "delta", "text": piece.text})
        except ChatTimeoutError:
            yield _sse_event(
                {
                    "event": "error",
                    "code": "llm_timeout",
                    "detail": "답변이 늦어지고 있어요. 다시 시도해 주세요",
                }
            )
            return
        except ChatGenerationError:
            yield _sse_event(
                {
                    "event": "error",
                    "code": "llm_failed",
                    "detail": "답변 생성에 실패했어요. 다시 시도해 주세요",
                }
            )
            return

        assert answer is not None  # stream_answer 는 항상 Answer 로 끝나거나 예외를 던진다

        # 답변 생성에 걸린 시간이 있어 보통은 자연히 뒤가 되지만, 즉시 돌아오는
        # 경우까지 생각해 **반드시 뒤**가 되게 못박는다.
        answered_at = max(datetime.now(KST), asked_at + timedelta(milliseconds=1))
        reply = ChatMessage(
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content=answer.content,
            referenced_place_ids=answer.referenced_place_ids or None,
            model_name=answer.model_name,
            created_at=answered_at,
        )
        db.add(reply)
        # 답변까지 왔으면 그 시각이 "마지막으로 이야기한 때"다.
        touch_conversation(conversation, answered_at)
        db.commit()
        db.refresh(reply)

        notification = add_notification(
            db,
            user_id=current_user.id,
            type="chat_answer_ready",
            target_id=conversation_id,
            title="혼디의 답변이 도착했어요",
            content="요청하신 답변이 완성됐어요.",
        )
        db.commit()
        # 완료 이벤트를 내보내기 전에 발송해, 클라이언트가 스트림을 닫더라도
        # 이미 생성된 답변의 푸시가 빠지는 구간을 없앤다.
        send_pushes(db, notification)

        summaries = places_of(db, [reply])
        yield _sse_event(
            {
                "event": "done",
                "assistantMessage": _to_message_item(reply, summaries).model_dump(
                    mode="json", by_alias=True
                ),
            }
        )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
