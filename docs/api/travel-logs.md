# 여행 기록 API

작성일: 2026-08-12 · 상태: **확정 규약 반영** (2026-08-12 팀 회의)

공통 규약은 [`README.md`](./README.md)를 따릅니다.

관련 DB 테이블: `travel_logs`, `travel_log_pets`
엔드포인트 스텁 파일은 `trips.py`이지만 대응 테이블은 `travel_logs`입니다.

---

## 개념 정리

여행 기록 한 건과 AI 생성 이미지는 `travel_logs` 한 행입니다.

```text
원본 사진 업로드
  → writingStyle · mood 선택
  → AI가 손글씨·장식 이미지 생성
  → generatedImageUrl 완성
```

`originalImageUrl`은 재생성·편집용으로만 쓰고, 목록·공유에는 항상 `generatedImageUrl`을 씁니다.

### 여행과의 관계

`routeId`가 있으면 특정 여행에 속한 기록이고, `null`이면 개별 기록입니다.
앱은 개별 기록을 **월 단위로 묶어** 보여줍니다.

> **이름 주의** — 앱 [`types/travelLog.ts`](../../apps/mobile/src/types/travelLog.ts)는 `tripId`를 쓰지만
> DB 컬럼은 `travel_logs.route_id`입니다. **API는 `routeId`를 씁니다.**
>
> 같은 파일 48번 줄 주석에 `DB의 trip_pets` 라고 적혀 있으나 **그런 테이블은 없습니다.**
> 여행 자체의 반려동물은 `route_request_pets`, 기록별 반려동물은 `travel_log_pets`입니다.

---

## 엔드포인트 목록

| Method | Path | 설명 | 인증 |
| --- | --- | --- | --- |
| GET | `/travel-logs` | 기록 목록 | 필요 |
| GET | `/travel-logs/groups` | 여행·월 단위로 묶은 목록 | 필요 |
| POST | `/travel-logs` | 기록 생성 및 이미지 생성 시작 | 필요 |
| GET | `/travel-logs/{logId}` | 기록 상세 | 필요 |
| GET | `/travel-logs/{logId}/status` | 이미지 생성 상태 | 필요 |
| POST | `/travel-logs/{logId}/regenerate` | 이미지 재생성 | 필요 |
| PATCH | `/travel-logs/{logId}` | 기록 수정 | 필요 |
| DELETE | `/travel-logs/{logId}` | 기록 삭제 | 필요 |

---

## GET /travel-logs

### 요청

```text
GET /api/v1/travel-logs?routeId=...&petIds=...&from=2026-08-01&to=2026-08-31
```

| 파라미터 | 기본값 | 설명 |
| --- | --- | --- |
| `routeId` | — | 특정 여행의 기록만. `none`이면 여행 없는 개별 기록만 |
| `petIds` | — | 함께한 반려동물로 필터. 여러 개면 OR |
| `placeQuery` | — | `placeNameSnapshot` 검색 |
| `from` `to` | — | `recordedDate` 범위 |
| `limit` | 20 | 최대 100 |
| `offset` | 0 | |

### 응답 `200`

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "routeId": "...",
      "placeId": "...",
      "placeNameSnapshot": "함덕해수욕장",
      "recordedDate": "2026-09-10",
      "visitedAt": "2026-09-10T14:30:00+09:00",
      "originalImageUrl": "https://...",
      "generatedImageUrl": "https://...",
      "writingStyle": "dog_diary",
      "mood": "happy",
      "generationStatus": "completed",
      "personalMessage": "몽이가 처음 본 바다",
      "isRepresentative": true,
      "companions": [
        {
          "petId": "...",
          "nameSnapshot": "몽이",
          "profileImageSnapshot": "https://..."
        }
      ],
      "createdAt": "2026-09-10T15:00:00+09:00"
    }
  ],
  "total": 27,
  "limit": 20,
  "offset": 0
}
```

기본 정렬은 `recordedDate` 최신순이며, 같은 날짜 안에서는 `visitedAt` → `createdAt` 순입니다.

### 주의할 필드

| 필드 | 설명 |
| --- | --- |
| `recordedDate` | **날짜** (`2026-09-10`). 날짜 그룹핑 기준 |
| `visitedAt` | **시각**. 리뷰의 `visitedAt`은 날짜라 형식이 다름 |
| `placeNameSnapshot` | 장소명이 바뀌거나 삭제돼도 기록에 남는 이름 |
| `companions` | `travel_log_pets`. 반려동물을 삭제해도 이름·사진이 남음 |
| `generationStatus` | `idle` `uploading` `generating` `completed` `failed` |
| `writingStyle` | `dog_diary` `jeju_dialect` |
| `mood` | `happy` `excited` `relaxed` `bittersweet`. `null` 가능 |

`companions`의 `petId`는 `ON DELETE SET NULL`이라 반려동물을 완전히 지우면 `null`이 될 수 있습니다.
그래도 `nameSnapshot`은 남아 화면이 깨지지 않습니다.

값 표기는 [`logDraft.ts`](../../apps/mobile/src/types/logDraft.ts)가 이미 DB와 일치합니다.
`writingStyle` `mood` `generationStatus` 세 타입은 수정할 필요가 없습니다.

---

## GET /travel-logs/groups

앱 목록 화면은 기록을 **여행 단위 / 월 단위**로 묶어 보여줍니다.
앱이 매번 직접 묶지 않도록 서버가 그룹을 만들어 내려줍니다.

### 응답 `200`

```json
{
  "items": [
    {
      "kind": "route",
      "route": {
        "id": "...",
        "title": "몽이랑 제주 2박 3일",
        "startDate": "2026-09-10",
        "endDate": "2026-09-12",
        "placeNameSnapshot": "함덕해수욕장",
        "companions": [
          { "petId": "...", "nameSnapshot": "몽이", "profileImageSnapshot": "https://..." }
        ],
        "logCount": 5,
        "previewLogs": []
      }
    },
    {
      "kind": "ungrouped",
      "group": {
        "year": 2026,
        "month": 8,
        "logCount": 3,
        "previewLogs": []
      }
    }
  ],
  "total": 6,
  "limit": 20,
  "offset": 0
}
```

`previewLogs`에는 `GET /travel-logs` 항목과 같은 구조의 기록이 최대 4건 들어갑니다.
콜라주 미리보기용이며, 항상 실제 기록에서 가져옵니다.

`route.companions`는 **여행 자체의 반려동물**(`route_request_pets`)이고,
각 기록의 `companions`(`travel_log_pets`)와는 다른 데이터입니다. 어느 한쪽만 고치지 않습니다.

`logCount`는 그 그룹에 속한 기록 수입니다.
마이페이지의 `travelLogsCount`(내 전체 기록 수)와는 집계 범위가 다릅니다.

---

## 여행 모아보기 화면 구성

앱의 [`TripMemoryScreen`](../../apps/mobile/src/features/travel-logs/TripMemoryScreen.tsx)은
여행 하나에 속한 기록을 날짜별로 묶어 보여줍니다.
화면 파라미터 이름은 `tripId`이지만 **실제로 담기는 값은 `routeId`입니다.**

이 화면에는 전용 엔드포인트가 없습니다. 기존 두 개를 조합합니다.

| 화면 영역 | 엔드포인트 | 쓰는 필드 |
| --- | --- | --- |
| 헤더 | [`GET /routes/{routeId}`](./routes.md) | `title` `startAt` `endAt` `logCount` |
| 본문 | `GET /travel-logs?routeId={routeId}` | 기록 목록 |

[`useTripMemoryLogs.ts`](../../apps/mobile/src/features/travel-logs/hooks/useTripMemoryLogs.ts)가
이미 헤더용·본문용 두 번의 조회로 나눠 부르고 있어 구조가 그대로 맞습니다.

`logCount`는 `GET /routes` **목록**에는 있었으나 **상세**에는 빠져 있어 추가했습니다
([`routes.md`](./routes.md) 참고).

월 단위로 묶인 개별 기록(`kind`가 `ungrouped`)은 대응하는 여행이 없으므로
`GET /travel-logs?routeId=none&from=...&to=...`로 조회합니다.

---

## POST /travel-logs

기록을 만들고 AI 이미지 생성을 시작합니다. 생성이 오래 걸리므로 **`202`를 즉시 돌려줍니다.**

### 요청

```json
{
  "routeId": null,
  "placeId": "550e8400-e29b-41d4-a716-446655440000",
  "placeName": "함덕해수욕장",
  "recordedDate": "2026-09-10",
  "visitedAt": "2026-09-10T14:30:00+09:00",
  "originalImageUrl": "https://...",
  "writingStyle": "dog_diary",
  "mood": "happy",
  "personalMessage": "몽이가 처음 본 바다",
  "petIds": ["550e8400-e29b-41d4-a716-446655440000"]
}
```

| 필드 | 필수 | 설명 |
| --- | --- | --- |
| `recordedDate` | ✅ | 날짜 |
| `originalImageUrl` | ✅ | 업로드한 원본 |
| `writingStyle` | ✅ | `dog_diary` `jeju_dialect` |
| `placeId` | — | 없으면 `placeName` 필수 |
| `placeName` | 조건부 | `placeNameSnapshot`으로 저장 |
| `petIds` | — | 저장 시점의 이름·사진을 스냅샷으로 복사 |
| `mood` | — | |

`placeId`를 보내도 서버가 그 시점의 장소명을 `placeNameSnapshot`에 복사합니다.
장소가 나중에 삭제되거나 이름이 바뀌어도 기록 화면이 유지됩니다.

`petIds`도 마찬가지로 이름과 프로필 사진을 `travel_log_pets`에 스냅샷으로 저장합니다.
`(travel_log_id, pet_id)`에 UNIQUE 제약이 있어 같은 반려동물을 중복으로 넣을 수 없습니다.

`originalImageUrl`은 **필수**이며, [`uploads.md`](./uploads.md)의 `POST /uploads`로 먼저 받습니다
(`purpose`는 `travel_log`). 업로드가 끝나기 전에는 이 요청을 보낼 수 없습니다.

`generatedImageUrl`은 앱이 올리지 않습니다. AI 생성 후 서버가 직접 저장합니다.

### 응답 `202`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "generationStatus": "generating"
}
```

### 에러

| 코드 | 상황 |
| --- | --- |
| 403 | 다른 사용자의 `petId` 또는 `routeId` |
| 422 | `writingStyle`·`mood` 값 오류, 미래 `recordedDate` |

---

## GET /travel-logs/{logId}

기록 하나만 조회합니다.

### 응답 `200`

`GET /travel-logs`의 항목 하나와 동일한 구조입니다.

**목록 화면에서 사진을 눌러 크게 볼 때는 이 요청이 필요 없습니다.**
이미 받아둔 목록에서 찾아 쓰면 됩니다. 앱의 `MemoryPhotoModal`이 그렇게 동작합니다.

목록을 거치지 않고 기록 하나로 바로 들어오는 경우에 씁니다.

```text
알림·딥링크로 특정 기록을 바로 여는 경우
이미지 생성이 끝난 뒤 최신 상태를 다시 읽는 경우
```

### 에러

| 코드 | 상황 |
| --- | --- |
| 403 | 다른 사용자의 기록 |
| 404 | 없는 `logId` |

---

## GET /travel-logs/{logId}/status

생성 진행 상태만 확인합니다.

### 응답 `200`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "generationStatus": "generating"
}
```

완료되면 결과 URL이 함께 옵니다.

```json
{
  "id": "...",
  "generationStatus": "completed",
  "generatedImageUrl": "https://..."
}
```

실패한 경우입니다.

```json
{ "id": "...", "generationStatus": "failed" }
```

`travel_logs`에 실패 사유 컬럼이 없어 사유는 내려주지 않습니다.
앱은 재생성 버튼만 보여줍니다.

---

## POST /travel-logs/{logId}/regenerate

같은 원본 사진으로 이미지를 다시 만듭니다. `writingStyle`과 `mood`를 바꿔서 보낼 수 있습니다.

### 요청

```json
{ "writingStyle": "jeju_dialect", "mood": "excited" }
```

두 필드 모두 선택입니다. 보내지 않으면 기존 값을 씁니다.

### 응답 `202`

```json
{ "id": "...", "generationStatus": "generating" }
```

`generatedImageUrl`은 새 이미지로 덮어씁니다. `originalImageUrl`은 그대로 둡니다.

---

## PATCH /travel-logs/{logId}

### 요청

```json
{
  "personalMessage": "다시 가고 싶은 날",
  "recordedDate": "2026-09-11",
  "isRepresentative": true,
  "petIds": ["..."]
}
```

보낸 필드만 수정합니다.

`isRepresentative`를 `true`로 바꾸면 **같은 날짜 그룹의 기존 대표는 자동으로 해제**됩니다.
DB에 제약이 없으므로 서버가 처리해야 합니다.

`petIds`를 보내면 `travel_log_pets`를 전부 지우고 새로 저장합니다.
이때 스냅샷도 현재 시점 값으로 갱신됩니다.

`originalImageUrl`과 `writingStyle`은 수정할 수 없습니다. 다시 만들려면 재생성을 씁니다.

### 에러

| 코드 | 상황 |
| --- | --- |
| 403 | 다른 사용자의 기록 |
| 404 | 없는 `logId` |

---

## DELETE /travel-logs/{logId}

물리 삭제입니다. `travel_logs`에 `deleted_at`이 없습니다.
`travel_log_pets`도 `ON DELETE CASCADE`로 함께 지워집니다.

### 응답 `204`

본문 없음.

> **[확인 필요]** 스토리지에 올라간 원본·생성 이미지 파일도 함께 지울지.
> DB 행만 지우면 파일이 남습니다.

---

## 변경 이력

| 날짜 | 내용 |
| --- | --- |
| 2026-08-12 | 초안 작성 |
| 2026-08-12 | 이미지 업로드 확인 필요 항목을 [`uploads.md`](./uploads.md) 참조로 교체. `originalImageUrl`이 필수임을 명시 |
| 2026-08-12 | 목록에만 있고 본문이 없던 `GET /travel-logs/{logId}` 명세 작성. 여행 모아보기 화면 구성 절 추가 (전용 엔드포인트 없이 `GET /routes/{routeId}` + `GET /travel-logs?routeId=` 조합) |
