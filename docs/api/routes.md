# 루트 추천 · 내 여행 API

작성일: 2026-08-12 · 상태: **확정 규약 반영** (2026-08-12 팀 회의)

공통 규약은 [`README.md`](./README.md)를 따릅니다.

관련 DB 테이블: `route_requests`, `route_request_pets`, `route_request_stays`,
`routes`, `route_days`, `route_items`, `route_moves`,
`route_checklist_items`, `route_memos`, `route_calculation_cache`

---

## 개념 정리

앱의 "루트 추천"과 "내 여행"은 **같은 데이터**입니다. 별도 테이블로 나누지 않고
`routes.status`로 구분합니다 ([DB 문서](../database/README.md) 참고).

```text
generating → generated → saved → ongoing → completed
                                        ↘ failed
```

| 상태 | 뜻 | 화면 |
| --- | --- | --- |
| `generating` | AI가 추천 생성 중 | 로딩 |
| `generated` | 추천 완료, 아직 저장 안 함 | 추천 결과 |
| `saved` | 사용자가 "내 여행"에 저장 | 내 여행 목록 |
| `ongoing` | 여행 중 | 내 여행 상세 |
| `completed` | 여행 종료 | 지난 여행 |
| `failed` | 생성 실패 | 재시도 안내 |

**요청(`route_requests`)과 결과(`routes`)는 별개 테이블**입니다.
같은 요청으로 여러 번 추천을 생성할 수 있고, 그때마다 `routes.version`이 올라갑니다.

프론트 타입과의 대응은 아래와 같습니다.

| 프론트 (`features/trips/types/trip.ts`) | DB |
| --- | --- |
| `Trip` | `routes` |
| `Schedule` | `route_days` |
| `ScheduleItem` | `route_items` |
| `ScheduleItem.moveToNext` | `route_moves` + 계산 캐시 |
| `ChecklistItem` | `route_checklist_items` |
| `TripMemo` | `route_memos` |

---

## 엔드포인트 목록

### 추천 생성

| Method | Path | 설명 | 인증 |
| --- | --- | --- | --- |
| POST | `/route-requests` | 추천 요청 생성 및 생성 시작 | 필요 |
| GET | `/routes/{routeId}/status` | 생성 진행 상태 확인 | 필요 |
| POST | `/routes/{routeId}/regenerate` | 같은 조건으로 재생성 | 필요 |

### 여행 조회·관리

| Method | Path | 설명 | 인증 |
| --- | --- | --- | --- |
| GET | `/routes` | 내 여행 목록 | 필요 |
| GET | `/routes/{routeId}` | 여행 상세 | 필요 |
| PATCH | `/routes/{routeId}` | 제목·메모·상태·키워드 수정 | 필요 |
| DELETE | `/routes/{routeId}` | 여행 삭제 | 필요 |
| GET | `/routes/shared/{shareToken}` | 공유 링크로 조회 | — |
| POST | `/routes/{routeId}/share` | 공유 링크 발급 | 필요 |

### 일정 편집

| Method | Path | 설명 | 인증 |
| --- | --- | --- | --- |
| POST | `/route-days/{routeDayId}/items` | 일정에 장소 추가 | 필요 |
| PATCH | `/route-items/{routeItemId}` | 일정 항목 수정 | 필요 |
| DELETE | `/route-items/{routeItemId}` | 일정 항목 삭제 | 필요 |
| PUT | `/route-days/{routeDayId}/items/order` | 순서 일괄 변경 | 필요 |

### 체크리스트 · 메모

| Method | Path | 설명 | 인증 |
| --- | --- | --- | --- |
| GET | `/routes/{routeId}/checklist-items` | 체크리스트 조회 | 필요 |
| POST | `/routes/{routeId}/checklist-items` | 항목 추가 | 필요 |
| PATCH | `/checklist-items/{itemId}` | 체크·라벨 수정 | 필요 |
| DELETE | `/checklist-items/{itemId}` | 항목 삭제 | 필요 |
| GET | `/routes/{routeId}/memos` | 메모 목록 | 필요 |
| POST | `/routes/{routeId}/memos` | 메모 작성 | 필요 |
| PATCH | `/memos/{memoId}` | 메모 수정 | 필요 |
| DELETE | `/memos/{memoId}` | 메모 삭제 | 필요 |

---

## POST /route-requests

여행 조건을 저장하고 AI 추천 생성을 시작합니다.
`route_requests` + `route_request_pets` + `route_request_stays`를 한 트랜잭션으로 저장합니다.

생성은 오래 걸리므로 **즉시 `202`를 돌려주고 백그라운드에서 진행**합니다.

### 요청

```json
{
  "title": "몽이랑 제주 2박 3일",
  "startAt": "2026-09-10T09:00:00+09:00",
  "endAt": "2026-09-12T18:00:00+09:00",
  "departureLocation": "제주국제공항",
  "departurePlaceId": null,
  "pace": "relaxed",
  "transport": "rental_car",
  "companionCount": 2,
  "preferredTags": ["바다", "카페"],
  "requestText": "산책하기 좋은 곳 위주로 부탁해요",
  "petIds": ["550e8400-e29b-41d4-a716-446655440000"],
  "stays": [
    {
      "placeId": null,
      "name": "함덕 펜션",
      "address": "제주특별자치도 제주시 조천읍 ...",
      "checkInAt": "2026-09-10T16:00:00+09:00",
      "checkOutAt": "2026-09-12T11:00:00+09:00"
    }
  ]
}
```

| 필드 | 필수 | 제약 |
| --- | --- | --- |
| `startAt` `endAt` | ✅ | `endAt > startAt` |
| `pace` | ✅ | `relaxed` `normal` `packed` |
| `transport` | ✅ | `rental_car` `own_car` `taxi` `public_transport` `walk` `ferry` `airplane` |
| `companionCount` | — | 기본 1. 1 이상 |
| `petIds` | — | 본인 소유 반려동물 |
| `stays[].checkOutAt` | — | `checkInAt`보다 뒤 |

`pace`와 `transport`, `preferredTags`는 **이번 여행 조건**입니다.
값을 보내지 않으면 사용자 기본 취향(`user_travel_preferences`)을 씁니다.

```text
이번 여행에서 직접 입력한 값 > 사용자 기본 취향 > 서비스 기본값
```

적용된 최종 값은 `route_requests`에 스냅샷으로 저장되므로, 나중에 기본 취향을 바꿔도
과거 추천 조건은 바뀌지 않습니다.

`petIds`의 외래키는 `ON DELETE RESTRICT`라, 이 요청에 묶인 반려동물은 물리 삭제되지 않습니다.

### 응답 `202`

```json
{
  "routeId": "550e8400-e29b-41d4-a716-446655440000",
  "routeRequestId": "...",
  "status": "generating",
  "version": 1
}
```

앱은 `routeId`로 상태를 확인하다가 `generated`가 되면 상세를 조회합니다.

### 에러

| 코드 | 상황 |
| --- | --- |
| 403 | 다른 사용자의 `petId` |
| 422 | `endAt <= startAt`, `companionCount < 1` |

---

## GET /routes/{routeId}/status

생성 진행 상태만 가볍게 확인합니다. 상세 조회보다 응답이 작아 반복 호출에 적합합니다.

### 응답 `200`

```json
{
  "routeId": "550e8400-e29b-41d4-a716-446655440000",
  "status": "generating",
  "version": 1
}
```

실패한 경우입니다.

```json
{
  "routeId": "...",
  "status": "failed",
  "version": 1,
  "failureReason": "추천할 장소를 찾지 못했습니다."
}
```

> **[확인 필요]** 폴링 간격과 타임아웃.
> `failureReason`을 저장할 컬럼이 `routes`에 없어, 실패 사유는 응답에서만 내려주거나
> 별도 컬럼 추가가 필요합니다. **컬럼을 임의로 추가하지 않았습니다.**

---

## GET /routes

내 여행 목록입니다.

### 요청

```text
GET /api/v1/routes?status=saved&limit=20&offset=0
```

| 파라미터 | 기본값 | 설명 |
| --- | --- | --- |
| `status` | 전체 | `generated` `saved` `ongoing` `completed` 등. 여러 개 가능 |
| `limit` | 20 | 최대 100 |
| `offset` | 0 | |

### 응답 `200`

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "몽이랑 제주 2박 3일",
      "status": "saved",
      "version": 1,
      "startAt": "2026-09-10T09:00:00+09:00",
      "endAt": "2026-09-12T18:00:00+09:00",
      "nights": 2,
      "days": 3,
      "pace": "relaxed",
      "transport": "rental_car",
      "coverImageUrl": "https://...",
      "styleKeywords": ["여유로운", "힐링"],
      "petSafetyScore": 92.5,
      "isPublic": false,
      "logCount": 5
    }
  ],
  "total": 3,
  "limit": 20,
  "offset": 0
}
```

`nights` `days` `logCount`는 계산값입니다. `startAt`/`endAt`과 `travel_logs`에서 구합니다.

---

## GET /routes/{routeId}

일자별 일정과 이동 정보를 모두 포함한 상세입니다.

### 응답 `200`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "몽이랑 제주 2박 3일",
  "status": "saved",
  "version": 1,
  "startAt": "2026-09-10T09:00:00+09:00",
  "endAt": "2026-09-12T18:00:00+09:00",
  "nights": 2,
  "days": 3,
  "pace": "relaxed",
  "transport": "rental_car",
  "explanation": "반려동물 동반 가능한 야외 장소 위주로 구성했습니다.",
  "totalScore": 88.0,
  "petSafetyScore": 92.5,
  "coverImageUrl": "https://...",
  "styleKeywords": ["여유로운", "힐링"],
  "memo": "선크림 챙기기",
  "isPublic": false,
  "shareToken": null,
  "logCount": 5,
  "pets": [
    { "id": "...", "name": "몽이", "species": "dog", "size": "small" }
  ],
  "stays": [
    {
      "id": "...",
      "placeId": null,
      "name": "함덕 펜션",
      "address": "제주특별자치도 ...",
      "checkInAt": "2026-09-10T16:00:00+09:00",
      "checkOutAt": "2026-09-12T11:00:00+09:00"
    }
  ],
  "distanceSummary": {
    "totalDistanceMeters": 128400,
    "totalDurationMinutes": 214
  },
  "routeDays": [
    {
      "id": "...",
      "dayNumber": 1,
      "routeDate": "2026-09-10",
      "title": "제주 동부 해안",
      "weather": {
        "condition": "sunny",
        "temperature": 27.5,
        "minTemperature": 22.0,
        "maxTemperature": 29.0,
        "precipitationProbability": 10
      },
      "items": [
        {
          "id": "...",
          "sortOrder": 0,
          "itemType": "attraction",
          "startsAt": "2026-09-10T10:00:00+09:00",
          "endsAt": "2026-09-10T11:30:00+09:00",
          "stayMinutes": 90,
          "note": null,
          "isSelected": true,
          "recommendationScore": 91.0,
          "recommendationReason": "반려동물 동반 가능하고 산책로가 넓습니다.",
          "place": {
            "id": "...",
            "name": "함덕해수욕장",
            "category": "beach",
            "primaryImageUrl": "https://...",
            "latitude": 33.5432,
            "longitude": 126.6695,
            "petPolicyType": "outdoor_only",
            "reviewCount": 37,
            "rating": 4.3
          },
          "customPlaceName": null,
          "moveToNext": {
            "transport": "rental_car",
            "distanceMeters": 8200,
            "durationMinutes": 17
          }
        }
      ]
    }
  ]
}
```

### 주의할 필드

| 필드 | 설명 |
| --- | --- |
| `place` | `place_id`가 있을 때. 직접 입력한 장소면 `null`이고 `customPlaceName`에 이름이 들어감 |
| `moveToNext` | 마지막 항목이면 `null`. `route_moves` + TMAP 계산 결과 |
| `distanceMeters` `durationMinutes` | **DB에 영구 저장하지 않습니다.** `route_calculation_cache`에 최대 24시간만 캐시하고 만료되면 다시 계산합니다 |
| `weather` | `route_days.weather_snapshot_id` 조인. 없으면 `null` |
| `isSelected` | 추천 항목 중 사용자가 뺀 것을 구분. 기본 `true` |
| `distanceSummary` | 계산값. 하위 `moveToNext` 합계 |
| `logCount` | 계산값. 이 여행에 속한 `travel_logs` 개수. 여행 모아보기 화면 헤더가 씀 ([`travel-logs.md`](./travel-logs.md)) |

`route_moves`에는 순서와 이동수단만 영구 저장하고, 거리·시간·polyline은 캐시에서 가져옵니다.

### 에러

| 코드 | 상황 |
| --- | --- |
| 403 | 다른 사용자의 여행 |
| 404 | 없는 `routeId` |

---

## PATCH /routes/{routeId}

### 요청

```json
{
  "title": "몽이랑 가을 제주",
  "status": "saved",
  "styleKeywords": ["여유로운", "바다"],
  "memo": "선크림 챙기기",
  "coverImageUrl": "https://..."
}
```

보낸 필드만 수정합니다. `status`는 아래 전이만 허용합니다.

```text
generated → saved
saved     → ongoing
ongoing   → completed
```

역방향이나 건너뛰는 전이는 `422`입니다.

### 에러

| 코드 | 상황 |
| --- | --- |
| 403 | 다른 사용자의 여행 |
| 404 | 없는 `routeId` |
| 422 | 허용되지 않는 상태 전이 |

---

## POST /routes/{routeId}/regenerate

같은 `route_request`로 추천을 다시 생성합니다.
기존 결과를 지우지 않고 **새 `version`으로 만듭니다**.

### 응답 `202`

```json
{
  "routeId": "새로 만들어진 routeId",
  "routeRequestId": "기존과 동일",
  "status": "generating",
  "version": 2
}
```

`(route_request_id, version)`에 UNIQUE 제약이 있습니다.

---

## DELETE /routes/{routeId}

물리 삭제입니다. `routes`에 `deleted_at`이 없습니다.
`route_days`, `route_items`, `route_moves`, `route_checklist_items`, `route_memos`가
`ON DELETE CASCADE`로 함께 지워집니다.

`travel_logs.route_id`는 `ON DELETE SET NULL`이라 **여행 기록은 남습니다.**
여행을 지워도 사진과 기록은 개별 기록으로 유지됩니다.

### 응답 `204`

---

## POST /routes/{routeId}/share

공유 링크를 발급합니다. `routes.share_token`을 생성하고 `is_public`을 `true`로 바꿉니다.

### 응답 `200`

```json
{
  "shareToken": "a1b2c3d4e5",
  "isPublic": true
}
```

이미 발급된 경우 기존 토큰을 그대로 돌려줍니다. `share_token`에 UNIQUE 제약이 있습니다.

공유 해제는 `PATCH /routes/{routeId}`로 `isPublic: false`를 보냅니다.

---

## GET /routes/shared/{shareToken}

인증 없이 공유된 여행을 봅니다.

### 응답 `200`

`GET /routes/{routeId}`와 같되 아래를 제외합니다.

```text
memo, shareToken, 체크리스트, 개인 메모
```

### 에러

| 코드 | 상황 |
| --- | --- |
| 404 | 없는 토큰 또는 `isPublic = false` |

---

## 일정 편집

### POST /route-days/{routeDayId}/items

```json
{
  "placeId": "550e8400-e29b-41d4-a716-446655440000",
  "itemType": "cafe",
  "sortOrder": 2,
  "startsAt": "2026-09-10T14:00:00+09:00",
  "stayMinutes": 60,
  "note": "테라스 자리"
}
```

| 필드 | 필수 | 제약 |
| --- | --- | --- |
| `itemType` | ✅ | `attraction` `restaurant` `cafe` `accommodation` `custom` |
| `sortOrder` | ✅ | 0 이상. 같은 날짜 안에서 UNIQUE |
| `placeId` | 조건부 | 없으면 `customPlaceName` 필수 |
| `customPlaceName` | 조건부 | 200자 |

`sortOrder`가 이미 있는 값이면 뒤 항목들을 밀어냅니다.

앱의 `PlaceCategory`는 `etc`를 쓰지만 DB `schedule_item_type`은 `custom`입니다.
**API는 `custom`을 씁니다.**

### PATCH /route-items/{routeItemId}

시각·체류시간·메모·`isSelected`를 수정합니다. `sortOrder` 변경은 아래 순서 API를 씁니다.

`endsAt`은 `startsAt`보다 뒤여야 하고, `stayMinutes`는 0 이상입니다.

### PUT /route-days/{routeDayId}/items/order

드래그로 순서를 바꿀 때 전체를 한 번에 보냅니다.
개별 `PATCH`를 여러 번 보내면 UNIQUE 제약 때문에 중간 상태에서 충돌합니다.

```json
{ "itemIds": ["item-3", "item-1", "item-2"] }
```

배열 순서대로 `sortOrder`가 0부터 다시 매겨집니다. 서버는 `route_moves`도 함께 갱신합니다.

### DELETE /route-items/{routeItemId}

물리 삭제입니다. 앞뒤 항목의 `route_moves`가 새로 연결되고 `sortOrder`가 다시 매겨집니다.

---

## 체크리스트

### GET /routes/{routeId}/checklist-items

```json
{
  "items": [
    {
      "id": "...",
      "category": "pet",
      "label": "배변봉투",
      "isChecked": false,
      "isRecommended": true,
      "sortOrder": 0
    }
  ],
  "total": 12,
  "limit": 100,
  "offset": 0
}
```

`isRecommended`가 `true`면 앱이 기본 제공한 항목, `false`면 사용자가 직접 추가한 항목입니다.

`category`는 DB에서 `String(30)` 자유 문자열입니다.
앱은 `pet` `travel` `etc`를 쓰고 있으며, 이 값을 그대로 사용합니다.

### POST /routes/{routeId}/checklist-items

```json
{ "category": "pet", "label": "간식", "sortOrder": 5 }
```

`isRecommended`는 서버가 `false`로 설정합니다. 사용자가 만든 항목이기 때문입니다.

### PATCH /checklist-items/{itemId}

```json
{ "isChecked": true }
```

라벨과 `sortOrder`도 수정 가능합니다.

### DELETE /checklist-items/{itemId}

물리 삭제입니다. 응답 `204`, 본문 없음.

`isRecommended`가 `true`인 기본 제공 항목도 지울 수 있습니다.
지운 뒤 추천 항목을 되돌리는 기능은 없습니다.

| 코드 | 상황 |
| --- | --- |
| 403 | 다른 사용자의 여행 |
| 404 | 없는 `itemId` |

---

## 메모

### GET /routes/{routeId}/memos

```json
{
  "items": [
    {
      "id": "...",
      "routeDayId": "...",
      "title": "1일차 준비물",
      "content": "차 안에 물그릇 두기",
      "createdAt": "2026-09-01T10:00:00+09:00",
      "updatedAt": "2026-09-01T10:00:00+09:00"
    }
  ],
  "total": 4,
  "limit": 20,
  "offset": 0
}
```

`routeDayId`가 `null`이면 여행 전체 메모, 값이 있으면 특정 일차 메모입니다.

앱의 `TripMemo.scheduleId`가 이 `routeDayId`에 대응합니다.

### POST /routes/{routeId}/memos

```json
{
  "routeDayId": null,
  "title": "준비물",
  "content": "선크림, 물그릇"
}
```

`content`만 필수입니다.

### PATCH /memos/{memoId}

```json
{ "title": "1일차 준비물", "content": "차 안에 물그릇 두기" }
```

보낸 필드만 수정합니다. `routeDayId`는 수정할 수 없습니다.
다른 일차로 옮기려면 삭제 후 다시 작성합니다.

| 코드 | 상황 |
| --- | --- |
| 403 | 다른 사용자의 메모 |
| 404 | 없는 `memoId` |

### DELETE /memos/{memoId}

물리 삭제입니다. 응답 `204`, 본문 없음.

| 코드 | 상황 |
| --- | --- |
| 403 | 다른 사용자의 메모 |
| 404 | 없는 `memoId` |

---

## 변경 이력

| 날짜 | 내용 |
| --- | --- |
| 2026-08-12 | 초안 작성 |
| 2026-08-12 | `GET /routes/{routeId}` 응답에 `logCount` 추가 — 목록에는 있었으나 상세에 빠져 있어 여행 모아보기 헤더를 그릴 수 없었음 |
| 2026-08-12 | 목록에만 있고 본문이 없던 `DELETE /checklist-items/{itemId}`, `PATCH`·`DELETE /memos/{memoId}` 명세 작성 |
