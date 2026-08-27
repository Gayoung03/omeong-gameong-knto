"""AI 챗봇 대화·메시지 API 스키마.

`referencedPlaces` 는 DB 에 저장된 모양과 다르다. `chat_messages` 에는
`referenced_place_ids`(UUID 배열)만 들어 있고, **응답에서는 장소 요약으로 펼쳐서**
내려준다(docs/api/chatbot.md). 앱이 ID 마다 장소를 다시 조회하지 않아도 되게
하기 위해서다.

`modelName` 은 답변을 만든 모델 이름이다. 사용자 메시지에는 없다.
"""

import uuid
from datetime import datetime

from pydantic import ConfigDict, Field

from app.db.models.enums import MessageRole, PetPolicyType
from app.schemas.base import APISchema


class ConversationCreate(APISchema):
    """대화를 시작한다.

    명세의 `firstMessage`(대화 생성과 동시에 질문 보내기)는 **여기 없다.**
    그 필드는 답변 생성이 있어야 의미가 있어서, 스트리밍 엔드포인트
    (`POST /chat/conversations/{id}/messages`)와 함께 붙인다.

    `title` 을 보내지 않으면 None 으로 남는다. 명세의 "없으면 서버가 첫 질문에서
    생성" 규칙도 첫 질문이 있어야 동작하므로 같은 시점에 들어온다.
    """

    route_id: uuid.UUID | None = None
    title: str | None = Field(default=None, max_length=150)


class ConversationUpdate(APISchema):
    """제목만 수정한다. `routeId` 는 바꿀 수 없다."""

    title: str = Field(min_length=1, max_length=150)


class ConversationCreated(APISchema):
    """대화를 막 만든 직후의 응답.

    `lastMessagePreview`·`messageCount` 가 **없다** — 메시지가 아직 하나도 없어
    항상 같은 값이기 때문이다(docs/api/chatbot.md 의 201 응답).
    """

    id: uuid.UUID
    title: str | None
    route_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class ConversationItem(APISchema):
    """대화 하나. **목록과 상세가 같은 스키마를 쓴다.**

    명세가 "`GET /chat/conversations` 의 항목 하나와 동일한 구조"라고 못박아 둬서,
    둘을 나누면 필드가 하나 늘 때마다 두 곳을 고쳐야 한다.

    `lastMessagePreview` 와 `messageCount` 는 DB 컬럼이 아니라 계산값이다.

    `routeId` 가 있으면 특정 여행에 대한 대화다. `ON DELETE SET NULL` 이라
    여행을 지워도 대화는 남는다.
    """

    id: uuid.UUID
    title: str | None
    route_id: uuid.UUID | None
    last_message_preview: str | None
    message_count: int
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(APISchema):
    items: list[ConversationItem]
    total: int
    limit: int
    offset: int


class ChatPlaceSummary(APISchema):
    """답변이 언급한 장소. 앱이 지도에 핀을 찍는 데 쓴다.

    장소 목록의 `PlaceListItem` 보다 훨씬 좁다 — 리뷰수·평점·즐겨찾기 여부처럼
    매번 세어야 하는 값을 빼서, 메시지 목록 한 번에 집계 쿼리가 딸려오지 않게 했다.
    """

    id: uuid.UUID
    name: str
    category: str
    #: 지도 마커 카드가 이름 아래에 그린다. 없으면 빈 줄이 남는다.
    address: str | None
    primary_image_url: str | None
    latitude: float
    longitude: float
    pet_policy_type: PetPolicyType


class MessageItem(APISchema):
    """메시지 한 건.

    `role` 에는 `system` 도 있다. 화면에 노출하지는 않지만 DB 에 저장될 수 있어
    타입에는 포함한다(docs/api/chatbot.md 확정 #6).
    """

    # `model_name` 은 Pydantic 이 예약해 둔 `model_` 로 시작한다. 비워주지 않으면
    # 필드를 만들 때마다 경고가 뜬다. 부모(APISchema)의 설정은 그대로 남고
    # 이 항목만 덧붙는다.
    model_config = ConfigDict(protected_namespaces=())

    id: uuid.UUID
    conversation_id: uuid.UUID
    role: MessageRole
    content: str
    referenced_places: list[ChatPlaceSummary] = Field(default_factory=list)
    model_name: str | None
    created_at: datetime


class MessageListResponse(APISchema):
    items: list[MessageItem]
    total: int
    limit: int
    offset: int


class MessageCreate(APISchema):
    """질문 한 건."""

    content: str = Field(min_length=1, max_length=2000)


class AnswerResponse(APISchema):
    """질문 하나에 저장된 **두 행**을 함께 돌려준다.

    명세는 이 엔드포인트를 SSE 스트림으로 정해뒀지만
    (`start` → `delta` → `done`), 지금은 **JSON 한 번에** 준다.
    앱에서 먼저 눌러볼 수 있게 하기 위해서다.

    두 필드가 각각 SSE 의 `start`·`done` 이 싣는 것과 같은 모양이라,
    스트리밍으로 옮길 때 **전달 방식만** 바뀌고 내용은 그대로다.
    """

    user_message: MessageItem
    assistant_message: MessageItem
