# AI 챗봇 API

작성일: 2026-08-12 · 상태: **확정 규약 반영** (2026-08-12 팀 회의)

공통 규약은 [`README.md`](./README.md)를 따릅니다.

관련 DB 테이블: `chat_conversations`, `chat_messages`

---

## 확정 #6 — `id` 타입 수정

앱 [`features/chatbot/types/chatbot.ts`](../../apps/mobile/src/features/chatbot/types/chatbot.ts)의
`ChatMessage.id`가 `number`인데 **DB는 UUID 문자열**입니다.
회의에서 UUID 문자열로 통일하기로 확정했습니다.

앱 타입이 DB와 어긋난 곳이 더 있어 함께 정리합니다.

| 앱 현재 | 변경 후 | DB |
| --- | --- | --- |
| `id: number` | `id: string` | `chat_messages.id` (UUID) |
| `text` | `content` | `chat_messages.content` |
| `role: 'user' \| 'assistant'` | `+ 'system'` | `message_role` 3종 |
| `mapPlaces?: Place[]` | `referencedPlaces` | `chat_messages.referenced_place_ids` |
| 없음 | `conversationId` | `chat_messages.conversation_id` |

`system` 역할은 화면에 노출하지 않지만, DB에 저장될 수 있으므로 타입에는 포함합니다.

---

## 엔드포인트 목록

| Method | Path | 설명 | 인증 |
| --- | --- | --- | --- |
| GET | `/chat/conversations` | 대화 목록 | 필요 |
| POST | `/chat/conversations` | 대화 시작 | 필요 |
| GET | `/chat/conversations/{conversationId}` | 대화 상세 | 필요 |
| PATCH | `/chat/conversations/{conversationId}` | 제목 수정 | 필요 |
| DELETE | `/chat/conversations/{conversationId}` | 대화 삭제 | 필요 |
| GET | `/chat/conversations/{conversationId}/messages` | 메시지 목록 | 필요 |
| POST | `/chat/conversations/{conversationId}/messages` | 질문 전송 | 필요 |

---

## GET /chat/conversations

### 응답 `200`

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "제주 동부 강아지 카페",
      "routeId": null,
      "lastMessagePreview": "함덕 근처 카페 세 곳을 추천드릴게요.",
      "messageCount": 8,
      "createdAt": "2026-08-10T14:00:00+09:00",
      "updatedAt": "2026-08-10T14:12:00+09:00"
    }
  ],
  "total": 3,
  "limit": 20,
  "offset": 0
}
```

기본 정렬은 `updatedAt` 최신순입니다. DB에 `(user_id, updated_at)` 인덱스가 있습니다.

`lastMessagePreview`와 `messageCount`는 계산값입니다.

`routeId`가 있으면 특정 여행에 대한 대화입니다.
`ON DELETE SET NULL`이라 여행을 지워도 대화는 남습니다.

---

## POST /chat/conversations

### 요청

```json
{
  "routeId": null,
  "title": null,
  "firstMessage": "제주 동부에 강아지랑 갈 만한 카페 알려줘"
}
```

| 필드 | 필수 | 설명 |
| --- | --- | --- |
| `firstMessage` | — | 있으면 대화 생성과 동시에 질문을 보냄 |
| `title` | — | 없으면 서버가 첫 질문에서 생성 |
| `routeId` | — | 특정 여행에 대한 대화일 때 |

### 응답 `201`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "제주 동부 강아지 카페",
  "routeId": null,
  "createdAt": "2026-08-10T14:00:00+09:00",
  "updatedAt": "2026-08-10T14:00:00+09:00"
}
```

`firstMessage`를 보냈으면 답변은 `POST .../messages`와 같은 방식으로 이어집니다.

---

## GET /chat/conversations/{conversationId}/messages

### 요청

```text
GET /api/v1/chat/conversations/{conversationId}/messages?limit=50&offset=0
```

### 응답 `200`

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "conversationId": "...",
      "role": "user",
      "content": "제주 동부에 강아지랑 갈 만한 카페 알려줘",
      "referencedPlaces": [],
      "modelName": null,
      "createdAt": "2026-08-10T14:00:00+09:00"
    },
    {
      "id": "...",
      "conversationId": "...",
      "role": "assistant",
      "content": "함덕 근처 카페 세 곳을 추천드릴게요.",
      "referencedPlaces": [
        {
          "id": "...",
          "name": "함덕 바다뷰 카페",
          "category": "cafe",
          "primaryImageUrl": "https://...",
          "latitude": 33.5432,
          "longitude": 126.6695,
          "petPolicyType": "indoor_allowed"
        }
      ],
      "modelName": "claude-sonnet-5",
      "createdAt": "2026-08-10T14:00:12+09:00"
    }
  ],
  "total": 8,
  "limit": 50,
  "offset": 0
}
```

정렬은 `createdAt` **오래된 순**입니다. 채팅 화면이 위에서 아래로 읽히기 때문에
다른 목록과 반대입니다.

### referencedPlaces

DB에는 `referenced_place_ids`(UUID 배열)만 저장하고, **응답에서는 장소 요약으로 펼쳐서** 내려줍니다.
앱이 ID마다 장소를 다시 조회하지 않아도 되도록 하기 위해서입니다.

앱의 `mapPlaces` 필드가 이 값에 대응합니다. 지도에 핀을 찍는 용도입니다.

장소가 나중에 삭제되면 그 항목은 배열에서 빠집니다. `referenced_place_ids`는 외래키가 아니라
단순 UUID 배열이라 참조 무결성이 보장되지 않습니다.

`modelName`은 답변을 만든 모델 이름입니다. 사용자 메시지에는 `null`입니다.

---

## POST /chat/conversations/{conversationId}/messages

질문을 보내고 답변을 받습니다. 사용자 메시지와 답변 메시지 **두 행**이 저장됩니다.

### 요청

```json
{ "content": "함덕 말고 서귀포 쪽은 어때?" }
```

### 응답 `201`

```json
{
  "userMessage": {
    "id": "...",
    "conversationId": "...",
    "role": "user",
    "content": "함덕 말고 서귀포 쪽은 어때?",
    "referencedPlaces": [],
    "modelName": null,
    "createdAt": "2026-08-10T14:05:00+09:00"
  },
  "assistantMessage": {
    "id": "...",
    "conversationId": "...",
    "role": "assistant",
    "content": "서귀포 쪽 카페 두 곳을 추천드릴게요.",
    "referencedPlaces": [],
    "modelName": "claude-sonnet-5",
    "createdAt": "2026-08-10T14:05:09+09:00"
  }
}
```

두 메시지를 함께 돌려주므로 앱이 목록을 다시 조회할 필요가 없습니다.

### 에러

| 코드 | 상황 |
| --- | --- |
| 403 | 다른 사용자의 대화 |
| 404 | 없는 `conversationId` |
| 422 | 빈 `content` |
| 502 | LLM 응답 실패 |
| 504 | LLM 응답 시간 초과 |

502·504일 때 **사용자 메시지는 이미 저장된 상태**입니다.
앱은 사용자 말풍선을 남겨두고 재시도 버튼을 보여주면 됩니다.

> **[확인 필요]** 답변 스트리밍 여부.
> 이 문서는 답변이 완성된 뒤 한 번에 돌려주는 방식으로 작성했습니다.
> 한 글자씩 보여주려면 SSE(`text/event-stream`)로 바꿔야 하고, 그러면 응답 형식이 완전히 달라집니다.
> 저장소에 `app/rag/` 디렉터리가 준비돼 있으나 아직 비어 있어 검색 방식도 정해지지 않았습니다.

---

## PATCH /chat/conversations/{conversationId}

```json
{ "title": "서귀포 카페 찾기" }
```

제목만 수정합니다.

---

## DELETE /chat/conversations/{conversationId}

물리 삭제입니다. `chat_messages`도 `ON DELETE CASCADE`로 함께 지워집니다.

### 응답 `204`

---

## 변경 이력

| 날짜 | 내용 |
| --- | --- |
| 2026-08-12 | 초안 작성. 확정 #6(`id`를 UUID 문자열로)과 앱 타입 정리 반영 |
