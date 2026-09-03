# AI 챗봇 API

작성일: 2026-08-12 · 갱신: 2026-08-18 · 상태: **RAG 검색 방식만 미정 — 그 외 구현 착수 가능**

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
| DELETE | `/chat/conversations/{conversationId}` | 대화 삭제(소프트) | 필요 |
| POST | `/chat/conversations/{conversationId}/restore` | 대화 복구 | 필요 |
| GET | `/chat/conversations/{conversationId}/messages` | 메시지 목록 | 필요 |
| POST | `/chat/conversations/{conversationId}/messages` | 질문 전송 **(SSE 스트림)** | 필요 |

마지막 하나만 응답이 JSON이 아니라 `text/event-stream`입니다. 나머지는 공통 규약대로입니다.

---

## GET /chat/conversations

### 요청

| 쿼리 | 타입 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `limit` | int (1~100) | 20 | |
| `offset` | int (0~) | 0 | |
| `deleted` | bool | `false` | `true`면 **휴지통**(지운 대화)을 지운 순서로 |

`deleted=true`도 응답 스키마가 같습니다. 앱은 목록 화면 코드를 그대로 재사용합니다.

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

> **`firstMessage`는 아직 구현돼 있지 않습니다.** 답변 생성이 있어야 의미가 있는
> 필드라 스트리밍 엔드포인트와 함께 붙입니다. 지금 보내면 무시됩니다.
>
> `title`의 "없으면 서버가 첫 질문에서 생성"은 **구현돼 있습니다** — 생성 시점은
> `POST .../messages`의 질문 커밋(start) 시점이고, 그 대화의 첫 메시지일 때만
> 첫 질문을 30자 문장 경계에서 잘라 저장합니다. `title`을 이미 지정했거나
> PATCH 로 바꾼 대화는 건드리지 않습니다. (2026-09-02)

### 에러

| 코드 | 상황 |
| --- | --- |
| 403 | 다른 사용자의 `routeId` |
| 404 | 없는 `routeId` |
| 409 | 대화 개수 상한(100개) 초과 |

`409`는 **자동으로 지우지 않기 때문에** 필요합니다. 오래된 대화를 말없이 지우면
사용자가 아껴둔 기록이 사라지므로, 만들지 못하게 막고 직접 지우도록 안내합니다
([`chatbot-design-decisions.md`](../planning/chatbot-design-decisions.md) D2).

---

## GET /chat/conversations/{conversationId}

대화 하나의 정보입니다. **메시지는 포함하지 않습니다.**

### 응답 `200`

`GET /chat/conversations`의 항목 하나와 동일한 구조입니다.

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "제주 동부 강아지 카페",
  "routeId": null,
  "lastMessagePreview": "함덕 근처 카페 세 곳을 추천드릴게요.",
  "messageCount": 8,
  "createdAt": "2026-08-10T14:00:00+09:00",
  "updatedAt": "2026-08-10T14:12:00+09:00"
}
```

메시지를 함께 내리지 않는 이유는 개수가 많을 수 있어 페이지네이션이 필요하기 때문입니다.
대화 화면은 이 요청과 `GET .../messages`를 함께 부릅니다.

제목만 있으면 되는 경우(대화 목록을 거치지 않고 바로 들어올 때)는 이 요청만으로 충분합니다.

### 에러

| 코드 | 상황 |
| --- | --- |
| 403 | 다른 사용자의 대화 |
| 404 | 없는 `conversationId` |

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
          "address": "제주특별자치도 제주시 조천읍 조함해안로 525",
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

**이 엔드포인트만 JSON을 돌려주지 않습니다.** 답변을 한 글자씩 흘려보내는
SSE(Server-Sent Events) 스트림입니다. **[확정]** (2026-08-18)

### 요청

```json
{ "content": "함덕 말고 서귀포 쪽은 어때?" }
```

```text
POST /api/v1/chat/conversations/{conversationId}/messages
Content-Type: application/json
Accept: text/event-stream
Authorization: Bearer <accessToken>
```

### 응답 `200` — `text/event-stream`

```text
Content-Type: text/event-stream
Cache-Control: no-cache
```

정상 흐름의 이벤트는 세 종류입니다. 순서대로 `start` → `delta`(여러 번) → `done`입니다.
실패하면 `done` 대신 `error`가 옵니다(아래 에러 절).

```text
data: {"event":"start","userMessage":{"id":"7c9e...","role":"user","content":"함덕 말고 서귀포 쪽은 어때?","createdAt":"2026-08-10T14:05:00+09:00"}}

data: {"event":"delta","text":"서귀포 쪽 "}

data: {"event":"delta","text":"카페 두 곳을 "}

data: {"event":"delta","text":"추천드릴게요."}

data: {"event":"done","assistantMessage":{"id":"a3f1...","role":"assistant","content":"서귀포 쪽 카페 두 곳을 추천드릴게요.","referencedPlaces":[],"modelName":"claude-sonnet-5","createdAt":"2026-08-10T14:05:09+09:00"}}
```

| 이벤트 | 담는 것 | 앱이 할 일 |
| --- | --- | --- |
| `start` | 저장된 **사용자 메시지** 전체 | 사용자 말풍선을 확정 ID로 교체 |
| `delta` | 답변 조각 `text` | 답변 말풍선에 이어 붙이기 |
| `done` | 저장된 **답변 메시지** 전체 | 말풍선을 최종 값으로 교체 |

`delta`를 이어 붙인 결과와 `done`의 `content`는 같습니다.
`done`을 따로 내리는 이유는 **저장된 `id`와 `referencedPlaces`가 그때 확정되기 때문**입니다.
`referencedPlaces`는 답변 생성이 끝나야 알 수 있어 조각으로 나눠 보내지 않습니다.

### 중간에 끊기면 저장하지 않습니다 **[확정]** (2026-08-18)

앱이 종료되거나 네트워크가 끊겨 `done`을 받지 못하면,
**서버는 그때까지 만든 답변을 저장하지 않습니다.**

```text
사용자 메시지   → 저장됨 (start 시점에 이미 저장)
잘린 답변       → 저장 안 함
```

잘린 답변이 대화 기록에 남으면 다음 질문의 맥락이 어긋나고, 사용자가 다시 열었을 때
문장이 중간에 끊긴 말풍선을 보게 됩니다. 사용자 메시지만 남으므로 앱은 재시도 버튼을
보여주면 됩니다.

### 중지 버튼도 같은 규칙을 따릅니다 **[확정]** (2026-08-30)

앱에 **답변 생성 중지 버튼이 있습니다.** 누르면 앱이 **연결을 끊을 뿐**이고,
중단 신호를 따로 보내지 않습니다. 그래서 서버는 사용자가 멈춘 것과 네트워크가
끊긴 것을 **구분하지 않고 똑같이** 처리합니다 — 위 규칙 그대로, 그때까지 만든
답변은 저장하지 않습니다.

```text
중지 버튼      →  연결 끊김  →  질문만 남고 답변은 저장 안 함
네트워크 끊김  →  연결 끊김  →  (같음)
```

앞서 이 절에는 *"중지 버튼은 이번 범위에 없다 — 중단 신호를 보낼 방법과 '여기까지는
저장' 규칙이 함께 필요하다"*고 적혀 있었습니다. **둘 다 필요 없게 만들어서** 해결했습니다.
"여기까지 저장"을 포기하면 새 엔드포인트도, 신호와 연결 끊김 사이의 순서 경합도
생기지 않습니다. 사용자에게는 "중지 = 답변 취소"로 읽히고, 질문은 남아 있어
다시 물어볼 수 있습니다.

> 중지 시점까지의 답변을 **저장하고 싶어지면** 그때 다시 엽니다. 저장을 요구하는
> 순간 "누가 끊었는지"를 서버가 알아야 하고, 그 방법이 다시 안건이 됩니다
> ([`chatbot-design-decisions.md`](../planning/chatbot-design-decisions.md) 3장).

### 에러

스트림이 **시작되기 전**에는 일반 JSON으로 내려갑니다.

| 코드 | 상황 |
| --- | --- |
| 403 | 다른 사용자의 대화 |
| 404 | 없는 `conversationId` |
| 422 | 빈 `content` |

스트림이 **시작된 뒤**에 실패하면 HTTP 상태 코드를 바꿀 수 없으므로 이벤트로 내립니다.

```text
data: {"event":"error","code":"llm_failed","detail":"답변 생성에 실패했어요. 다시 시도해 주세요."}
```

| `code` | 상황 |
| --- | --- |
| `llm_failed` | LLM 응답 실패 (기존 `502`에 해당) |
| `llm_timeout` | LLM 응답 시간 초과 (기존 `504`에 해당) |

`error` 이벤트를 받으면 앱은 스트림을 닫고 재시도 버튼을 보여줍니다.
이때도 **사용자 메시지는 이미 저장된 상태**라 말풍선을 지우지 않아도 됩니다.

> **[확인 필요]** 검색(RAG) 방식은 여전히 미정입니다.
> `app/rag/{ingestion,prompts,retrieval}` 골격만 있고 비어 있습니다.
> 이 절의 스트림 형식은 검색 방식과 무관하므로 구현을 막지는 않습니다.

---

## PATCH /chat/conversations/{conversationId}

```json
{ "title": "서귀포 카페 찾기" }
```

제목만 수정합니다.

---

## DELETE /chat/conversations/{conversationId}

**소프트 삭제입니다** (2026-09-03 변경). `chat_conversations.deleted_at`만 채우고
`chat_messages`는 **한 행도 지우지 않습니다.**

사용자가 대화를 지우는 것은 "안 보이게 해달라"는 뜻이지 "기록을 없애달라"는 뜻이
아니라고 보았습니다. 그래서 목록에서만 빼고, 휴지통에서 되살릴 수 있게 남깁니다.

지운 뒤에는 그 대화가 **없는 것처럼** 동작합니다 — 상세·제목 수정·재삭제·메시지 목록·
질문 전송이 모두 `404`입니다. 목록에서 사라졌는데 id로는 열리면 사용자가 혼란스럽습니다.

지운 대화는 **대화 개수 상한(100개)에 잡히지 않습니다.** "안 쓰는 대화를 지워주세요"라고
안내하므로, 지우면 실제로 자리가 나야 합니다.

### 응답 `204`

---

## POST /chat/conversations/{conversationId}/restore

휴지통에서 되살립니다.

`updated_at`은 **건드리지 않습니다.** 갱신하면 복구한 대화가 목록 맨 위로 튀어 오르는데,
되살렸을 때 기대하는 것은 "원래 있던 자리로 돌아오는 것"입니다.

### 응답 `200`

`GET /chat/conversations`의 항목 하나와 같은 구조(`ConversationItem`)입니다.

### 에러

| 코드 | 상황 |
| --- | --- |
| `404` | 없는 대화이거나, **휴지통에 없는 대화**(지우지 않은 대화를 복구하려 함) |
| `403` | 다른 사용자의 대화 (살아 있든 지워졌든 같은 응답) |
| `409` | 살아 있는 대화가 이미 100개라 되살릴 자리가 없음 |

---

## 변경 이력

| 날짜 | 내용 |
| --- | --- |
| 2026-08-12 | 초안 작성. 확정 #6(`id`를 UUID 문자열로)과 앱 타입 정리 반영 |
| 2026-08-18 | 답변을 **SSE 스트리밍**으로 확정. `POST /chat/conversations/{id}/messages` 전면 재작성 — `start`·`delta`·`done`·`error` 이벤트 정의, 중단 시 부분 답변 미저장, 중지 버튼은 범위 밖. 나머지 6개 엔드포인트는 변경 없음 |
| 2026-08-12 | 목록에만 있고 본문이 없던 `GET /chat/conversations/{conversationId}` 명세 작성 |
| 2026-09-03 | 삭제를 **물리 → 소프트**로 변경(`deleted_at`). `POST .../restore` 추가, `GET /chat/conversations`에 `deleted` 쿼리 추가, 개수 상한은 살아 있는 대화만 계산 |
| 2026-08-27 | 대화 CRUD 6개 구현하며 보완 — `POST /chat/conversations`에 에러 표 신설(`409` 대화 개수 상한), `firstMessage` 미구현 명시 |
| 2026-08-30 | **SSE 스트리밍 구현 완료.** 임시로 JSON을 돌려주던 `POST .../messages`가 명세대로 `start`→`delta`→`done`/`error`를 흘려보냅니다(응답 `200`, `text/event-stream`). **중지 버튼을 범위에 넣고 8/18 보류 조항을 해제**했습니다 — 앱은 연결만 끊고, 서버는 사용자 중지와 네트워크 끊김을 구분하지 않습니다("중간에 끊기면 저장 안 함"을 그대로 재사용). 새 엔드포인트 없음. **질문은 `start` 시점에 커밋**되므로 실패·중지해도 남습니다(JSON 시절의 "실패하면 질문도 저장 안 함"과 달라진 점) |
