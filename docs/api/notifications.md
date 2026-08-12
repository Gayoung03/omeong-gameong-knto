# 공지 · 알림 · 문의 API

작성일: 2026-08-12 · 상태: **확정 규약 반영** (2026-08-12 팀 회의)

공통 규약은 [`README.md`](./README.md)를 따릅니다.

관련 DB 테이블: `notices`, `notifications`, `inquiries`

이 세 도메인은 대응하는 엔드포인트 스텁 파일이 없습니다
(`app/api/v1/endpoints/`에 `notices.py`·`notifications.py`·`inquiries.py`가 없음).
구현 시 파일을 새로 만들어야 합니다.

알림 **수신 설정**(`users`의 두 컬럼)은 이 문서가 아니라 [`users.md`](./users.md)에 있습니다.

---

## 엔드포인트 목록

### 공지사항

| Method | Path | 설명 | 인증 |
| --- | --- | --- | --- |
| GET | `/notices` | 공지 목록 | — |
| GET | `/notices/{noticeId}` | 공지 상세 | — |

### 알림

| Method | Path | 설명 | 인증 |
| --- | --- | --- | --- |
| GET | `/notifications` | 알림 목록 | 필요 |
| GET | `/notifications/unread-count` | 안 읽은 개수 | 필요 |
| PATCH | `/notifications/{notificationId}/read` | 읽음 처리 | 필요 |
| POST | `/notifications/read-all` | 전체 읽음 처리 | 필요 |

### 1:1 문의

| Method | Path | 설명 | 인증 |
| --- | --- | --- | --- |
| GET | `/inquiries` | 내 문의 목록 | 필요 |
| POST | `/inquiries` | 문의 작성 | 필요 |
| GET | `/inquiries/{inquiryId}` | 문의 상세 | 필요 |

문의는 작성 후 수정·삭제할 수 없습니다. 답변이 달린 뒤 내용이 바뀌면 대화가 어긋나기 때문입니다.

---

## GET /notices

### 요청

```text
GET /api/v1/notices?limit=20&offset=0
```

### 응답 `200`

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "서비스 점검 안내",
      "isPinned": true,
      "publishedAt": "2026-08-10T09:00:00+09:00"
    }
  ],
  "total": 8,
  "limit": 20,
  "offset": 0
}
```

목록에는 `content`를 담지 않습니다. 상세에서 내려줍니다.

정렬은 **고정 공지 우선, 그다음 `publishedAt` 최신순**입니다.
DB에 `(is_active, is_pinned, published_at)` 인덱스가 있습니다.

`isActive`가 `false`인 공지는 목록·상세 어디에도 나오지 않습니다. 응답 필드로도 내려주지 않습니다.
`publishedAt`이 미래인 공지도 제외합니다.

> **필드명 정정** — 앱 [`types/notice.ts`](../../apps/mobile/src/types/notice.ts)는
> `createdAt`을 `'YYYY.MM.DD'` **표시용 문자열**로 갖고 있습니다.
> 화면 표시 형식을 데이터로 저장한 것이라, API는 `publishedAt`을 ISO 8601로 내려줍니다.
> 앱이 화면에서 포맷하면 됩니다.
>
> `notices.created_at`(행 생성 시각)과 `published_at`(공개 시각)은 다른 값입니다.
> 화면에 보여야 하는 건 `publishedAt`입니다.

---

## GET /notices/{noticeId}

### 응답 `200`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "서비스 점검 안내",
  "content": "8월 15일 새벽 2시부터 4시까지 점검이 진행됩니다.",
  "isPinned": true,
  "publishedAt": "2026-08-10T09:00:00+09:00"
}
```

### 에러

| 코드 | 상황 |
| --- | --- |
| 404 | 없는 `noticeId`, 비활성, 또는 아직 공개 전 |

---

## GET /notifications

앱 상단 종 버튼의 알림 목록입니다.

### 요청

```text
GET /api/v1/notifications?isRead=false&limit=20&offset=0
```

| 파라미터 | 기본값 | 설명 |
| --- | --- | --- |
| `isRead` | 전체 | `true` / `false` 필터 |
| `limit` | 20 | 최대 100 |
| `offset` | 0 | |

### 응답 `200`

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "type": "inquiry_answered",
      "title": "문의에 답변이 등록되었습니다",
      "content": "'반려동물 정보' 문의에 답변이 달렸어요.",
      "iconKey": "chat",
      "actionPath": "/settings/inquiries/550e8400-...",
      "isRead": false,
      "createdAt": "2026-08-11T10:00:00+09:00",
      "readAt": null
    }
  ],
  "total": 14,
  "limit": 20,
  "offset": 0
}
```

정렬은 `createdAt` 최신순입니다.

### 주의할 필드

| 필드 | 설명 |
| --- | --- |
| `type` | `String(30)` 자유 문자열. enum이 아님 |
| `iconKey` | 앱이 아이콘을 고르는 키. 이미지 URL이 아님 |
| `actionPath` | 알림을 눌렀을 때 이동할 **앱 내부 경로** |
| `readAt` | `isRead`가 `true`일 때만 값이 있음 |

DB CHECK 제약이 `is_read = false OR read_at IS NOT NULL`이라,
읽음 처리하면 `readAt`이 반드시 채워집니다.

`actionPath`는 서버가 앱 라우트를 알고 있어야 만들 수 있습니다.
앱 라우터 경로가 바뀌면 과거 알림의 링크가 깨집니다.

### 앱 타입과의 대조

2026-08-12 머지(PR #26)로 상단 바 알림 팝업이 추가되면서 앱에 알림 타입이 생겼습니다.
[`components/layout/notificationPreview.mock.ts`](../../apps/mobile/src/components/layout/notificationPreview.mock.ts)의
`NotificationPreview`입니다.

```ts
export type NotificationPreview = {
  id: string;
  icon: keyof typeof Ionicons.glyphMap;
  tone: 'primary' | 'sea';
  title: string;
  description: string;
};
```

| 앱 필드 | API / DB | 처리 |
| --- | --- | --- |
| `id: string` (`'weather'` `'pet'`) | `notifications.id` (UUID) | 목업 고정값 → UUID로 교체 |
| `title` | `title` | 일치 |
| `description` | `content` | **단어 불일치.** DB 단어를 따라 `content`로 통일 |
| `icon` | `iconKey` | 앱이 Ionicons 이름(`sunny-outline`)을 직접 사용 |
| `tone` | **DB 컬럼 없음** | 아래 참고 |

`NotificationPopup`은 목록만 그리고 항목에 `onPress`가 없어, 아직 `actionPath`를 쓰지 않습니다.
`isRead`·`createdAt`도 없습니다. 팝업이 미리보기 전용이기 때문이며,
전체 알림 화면(`app/notifications.tsx`)은 현재 `ComingSoonScreen`입니다.

> **[확인 필요] — `tone`을 담을 DB 컬럼이 없습니다.**
> 앱은 아이콘 배경을 귤(`primary`)과 바다(`sea`) 두 톤으로 번갈아 칠합니다.
> `notifications` 테이블에는 이 값을 담을 컬럼이 없습니다.
>
> 두 가지 선택지가 있습니다.
>
> | 안 | 내용 |
> | --- | --- |
> | 앱이 결정 | 목록 순서대로 번갈아 칠함. DB 변경 없음 |
> | 서버가 내려줌 | `notifications`에 컬럼 추가 필요 |
>
> 색상은 표현 영역이라 앱이 정하는 쪽을 권합니다. 컬럼은 추가하지 않았습니다.

> **[확인 필요]** `type`과 `iconKey`에 쓸 값 목록.
> DB가 자유 문자열(`String(30)`, `String(50)`)이라 제약이 없어,
> 서버와 앱이 같은 값을 쓰도록 목록을 합의해야 합니다.
> 목업에 쓰인 아이콘은 `sunny-outline`, `paw-outline` 두 개뿐입니다.
>
> `actionPath`를 서버가 만들지, `type` + 대상 ID만 내려주고 앱이 경로를 조립할지도 정해야 합니다.
> 후자가 라우트 변경에 강합니다.

---

## GET /notifications/unread-count

종 버튼의 빨간 점을 그리는 데만 쓰는 가벼운 조회입니다.

### 응답 `200`

```json
{ "unreadCount": 3 }
```

---

## PATCH /notifications/{notificationId}/read

### 요청

본문 없음.

### 응답 `204`

본문 없음. 서버가 `isRead = true`, `readAt = now()`로 기록합니다.
이미 읽은 알림이어도 `204`이고 `readAt`은 덮어쓰지 않습니다.

### 에러

| 코드 | 상황 |
| --- | --- |
| 403 | 다른 사용자의 알림 |
| 404 | 없는 `notificationId` |

---

## POST /notifications/read-all

### 응답 `200`

```json
{ "updatedCount": 3 }
```

이미 읽은 알림은 건드리지 않습니다.

---

## GET /inquiries

### 요청

```text
GET /api/v1/inquiries?status=pending&limit=20&offset=0
```

| 파라미터 | 설명 |
| --- | --- |
| `status` | `pending` `completed` |

### 응답 `200`

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "category": "반려동물 정보",
      "status": "pending",
      "title": "반려동물 정보를 수정할 수 없어요",
      "createdAt": "2026-08-11T10:00:00+09:00",
      "answeredAt": null
    }
  ],
  "total": 2,
  "limit": 20,
  "offset": 0
}
```

목록에는 `content`·`answer`·`imageUrls`를 담지 않습니다. 상세에서 내려줍니다.

정렬은 `createdAt` 최신순입니다.
DB에 `(user_id, status, created_at)` 인덱스가 있습니다.

> **[확인 필요]** `category` 값 목록.
> DB는 `String(50)` 자유 문자열이고, 앱
> [`types/inquiry.ts`](../../apps/mobile/src/types/inquiry.ts)는 한글 6종을 쓰고 있습니다.
>
> ```text
> 계정 및 회원정보 · 반려동물 정보 · 저장한 장소·코스 · 여행 일정 · 오류·불편 · 기타
> ```
>
> 확정 규약 #1(값은 영문 코드)을 따르면 `account` `pet` `saved` `schedule` `bug` `etc` 같은
> 코드로 바꾸고 앱이 한글 라벨로 변환해야 합니다.
> 다만 문의 분류는 운영자가 읽는 값이라 한글을 그대로 두는 선택지도 있습니다.
> **이 문서는 앱의 현재 한글 값을 그대로 예시에 썼습니다.**

---

## POST /inquiries

### 요청

```json
{
  "category": "반려동물 정보",
  "title": "반려동물 정보를 수정할 수 없어요",
  "content": "프로필 수정 화면에서 저장 버튼이 눌리지 않습니다.",
  "imageUrls": ["https://..."]
}
```

| 필드 | 필수 | 제약 |
| --- | --- | --- |
| `category` | ✅ | 50자 |
| `title` | ✅ | 200자 |
| `content` | ✅ | |
| `imageUrls` | — | `inquiries.image_urls` 배열에 저장 |

`status`는 서버가 `pending`으로 설정합니다.

문의 이미지는 별도 테이블 없이 배열 컬럼에 저장합니다
([DB 문서](../database/README.md) 참고).

`imageUrls`에 담을 주소는 [`uploads.md`](./uploads.md)의 `POST /uploads`로 미리 받습니다
(`purpose`는 `inquiry`).

### 응답 `201`

`GET /inquiries/{inquiryId}` 와 동일한 구조입니다.

### 에러

| 코드 | 상황 |
| --- | --- |
| 422 | 제목·내용 누락, 길이 초과 |

---

## GET /inquiries/{inquiryId}

### 응답 `200`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "category": "반려동물 정보",
  "status": "completed",
  "title": "반려동물 정보를 수정할 수 없어요",
  "content": "프로필 수정 화면에서 저장 버튼이 눌리지 않습니다.",
  "imageUrls": ["https://..."],
  "answer": "해당 문제는 8월 12일자 업데이트에서 수정되었습니다.",
  "answeredAt": "2026-08-12T11:00:00+09:00",
  "createdAt": "2026-08-11T10:00:00+09:00",
  "updatedAt": "2026-08-12T11:00:00+09:00"
}
```

`status`가 `completed`면 `answer`와 `answeredAt`이 반드시 있습니다.
DB CHECK 제약이 이를 보장합니다.

`status`가 `pending`이면 둘 다 `null`입니다.

> **날짜 형식 주의** — 앱 타입은 `createdAt`·`answeredAt`을 `'YYYY-MM-DD'` 날짜 문자열로
> 갖고 있는데 **DB는 시각**입니다. API는 시각으로 내려주고 앱이 화면에서 날짜만 표시합니다.

답변이 등록되면 `notifications`에 알림이 생성됩니다.
단, `users.inquiry_answer_notification_enabled`가 `false`인 사용자에게는 보내지 않습니다.

### 에러

| 코드 | 상황 |
| --- | --- |
| 403 | 다른 사용자의 문의 |
| 404 | 없는 `inquiryId` |

---

## 변경 이력

| 날짜 | 내용 |
| --- | --- |
| 2026-08-12 | 초안 작성 |
| 2026-08-12 | PR #26 머지 반영 — `NotificationPreview` 타입 추가에 따른 대조표, `tone` 컬럼 부재 기록 |
| 2026-08-12 | 문의 첨부 이미지 업로드 확인 필요 항목을 [`uploads.md`](./uploads.md) 참조로 교체 |
