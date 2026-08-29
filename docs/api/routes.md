# 루트 추천 · 내 여행 API

작성일: 2026-08-12 · 갱신: 2026-08-18 · 상태: **수동 여행 생성만 보류 — 그 외 구현 착수 가능**

공통 규약은 [`README.md`](./README.md)를 따릅니다.

관련 DB 테이블: `route_requests`, `route_request_pets`, `route_request_stays`,
`routes`, `route_pets`, `route_days`, `route_items`, `route_moves`,
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

### 추천 여행과 수동 여행

여행을 만드는 경로가 두 가지입니다. `routes.creation_type`으로 구분하며,
API 응답에서는 `creationType`으로 내려갑니다.

| `creationType` | 뜻 | `routeRequestId` | 펫 정보 |
| --- | --- | --- | --- |
| `recommended` | AI 추천으로 생성 | 있음 | `route_request_pets` |
| `manual` | 사용자가 직접 작성 | `null` | `route_pets` |

DB CHECK 제약(`creation_type_request_consistency`)이 이 조합을 강제합니다.
`recommended`인데 `routeRequestId`가 없거나, `manual`인데 있으면 저장되지 않습니다.

수동 여행은 추천 요청 없이 만들어지므로 `route_requests`에 행이 생기지 않습니다.
그래서 동반 반려동물을 `route_pets`(여행 ↔ 펫)에 직접 연결합니다.
`pets`로의 외래키가 `ON DELETE RESTRICT`라, 여행에 묶인 반려동물은 물리 삭제되지 않습니다.

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

### 수동 생성 **[보류 — 화면 기획 대기]** (2026-08-18 갱신)

| Method | Path | 설명 | 인증 |
| --- | --- | --- | --- |
| POST | `/routes` (미정) | 사용자가 직접 여행 작성 | 필요 |

**DB는 준비가 끝났습니다.** 마이그레이션 `8c71f4a2d9e0`이 아래를 추가했습니다.

| 추가된 것 | 역할 |
| --- | --- |
| `routes.creation_type` | `recommended` / `manual` 구분 |
| `routes.route_request_id` nullable | 수동 여행은 추천 요청서가 없음 |
| CHECK `creation_type_request_consistency` | 추천이면 요청서 필수, 수동이면 요청서 금지 |
| `route_pets` 테이블 | 수동 여행에 데려갈 반려동물을 직접 연결 |

```python
# routes.py:110-113 — 잘못된 조합은 DB가 거부합니다
"(creation_type = 'recommended' AND route_request_id IS NOT NULL) "
"OR (creation_type = 'manual' AND route_request_id IS NULL)"
```

**막고 있는 것은 "직접 만들기" 화면 기획 하나뿐입니다.** 저장할 곳도, 잘못된 데이터를
막을 규칙도 이미 있고 API 통로만 없습니다.

화면이 나오면 아래를 정합니다. 지금 시점의 유력안을 함께 적어 둡니다.

| 정할 것 | 유력안 |
| --- | --- |
| 경로 | `POST /routes` |
| 요청 범위 | **여행 껍데기(제목·기간·펫)만** 생성하고 일정은 기존 일정 편집 API로 채움 |
| 초기 `status` | `saved` (추천 흐름의 `generating`은 맞지 않음) |
| `version` | 재생성이 없으므로 항상 `1` |

요청 범위를 껍데기로 미는 이유는 두 가지입니다. 작성 도중 앱이 꺼져도 만든 여행이 남고,
일정 추가·수정 API가 어차피 필요해 재사용됩니다.

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

첫날 출발지는 `departureLocation`/`departurePlaceId`가 있으면 그 장소를 사용하고,
둘 다 없으면 첫 숙소를 사용합니다. 일정은 첫날 `선택한 출발지 → 추천 장소 → 숙소`,
중간 날짜 `숙소 → 추천 장소 → 숙소`, 마지막 날 `숙소 → 추천 장소` 순서로 조립합니다.

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
  "priorityPreset": "balanced",
  "userCriteria": ["pet", "proximity"],
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

숙소 좌표는 두 방식으로 결정합니다.

1. `stays[].placeId`가 있으면 `places.latitude/longitude`를 사용합니다.
2. `placeId`가 없으면 `stays[].address`를 카카오 주소 검색 API로 변환합니다.
   주소 결과가 없으면 카카오 키워드 검색 API로 장소명을 다시 조회합니다.

둘 다 보내면 DB 장소 좌표가 우선입니다. 숙소에는 `placeId` 또는 `address` 중 하나가
반드시 있어야 합니다. 현재 TMAP 일정 조립이 지원하는 이동수단은 `rental_car`,
`own_car`, `taxi`, `walk`이며 나머지는 `422`를 반환합니다.

`priorityPreset`에서 기본 가중치 배수를 적용한 다음 `userCriteria`로 사용자가 고른
항목을 추가 부스트하고, 합계가 1이 되도록 정규화합니다. 최종값만
`route_requests.applied_weights`에 저장합니다.

추천 생성 시 출발지(없으면 첫 숙소) 좌표를 기상청 5km 격자로 변환해 단기예보를
조회합니다. 여행 날짜들의 최대 강수확률을 `weather` 점수에 반영하며, 예보 범위를
벗어난 날짜이거나 기상청 호출이 실패하면 날씨 점수는 중립값으로 처리합니다.

일정 조립은 하루에 카페를 최대 한 곳만 배치하고, 저녁까지 이어지는 날짜의 마지막
방문을 17시 이후의 식당으로 구성합니다. 마지막 날 종료 시각이 17시 이전이면 그날은
저녁 식당을 강제하지 않습니다. `relaxed`는 장소 수만 줄이지 않고 방문 사이 여백과
저녁 식사 시간까지 확보합니다. 저녁 식사가 필요한 날짜에 조건을 통과한 식당이
부족하면 추천 생성을 실패로 처리하며, 식당이 아닌 장소로 조용히 대체하지 않습니다.

추천 생성 때마다 출발지와 숙소 주변의 한국관광공사 `KorService2/locationBasedList2`를
실시간 호출합니다. 응답 원문은 DB나 캐시에 저장하지 않으며, 제목·좌표가 일치하는
기존 DB 후보에만 `TourAPI 실시간 정보 확인` 출처를 표시합니다. 여행 설명에는 조회·대조
건수를 남겨 공모전 시연 화면에서 활용 여부를 확인할 수 있습니다. 호출 실패 시 기존 DB
추천은 유지하되 설명에 실패 사실을 표시합니다.

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
  "failureReason": "NO_RECOMMENDABLE_PLACES"
}
```

| `failureReason` | 사용자 안내 |
| --- | --- |
| `LOCATION_NOT_FOUND` | 출발지·숙소 위치 확인 필요 |
| `NO_RECOMMENDABLE_PLACES` | 조건에 맞는 장소 부족 |
| `DINNER_RESTAURANT_SHORTAGE` | 저녁 식당 후보 부족 |
| `ROUTE_PROVIDER_FAILED` | 이동 경로 제공자 실패 |
| `GENERATION_TIMEOUT` | 생성 시간 초과 |
| `UNKNOWN` | 분류하지 못한 실패 |

### 폴링 규칙 **[확정]** (2026-08-18)

```text
호출 간격    2초
타임아웃     3분  (앱이 폴링을 멈추고 실패 화면으로 전환)
```

2초보다 짧으면 서버 호출이 불필요하게 늘고, 길면 생성이 끝났는데도 로딩 화면이 남습니다.
3분이 지나도 `generating`이면 앱은 폴링을 멈추고 "잠시 후 다시 확인해 주세요"를 보여줍니다.
**서버가 생성을 중단하는 것은 아니므로**, 나중에 다시 들어오면 완료된 여행을 볼 수 있습니다.

### `failureReason`은 안전한 코드로 저장합니다 **[변경]** (2026-08-30)

추천 생성 실패 시 `routes.failure_reason`에 위 enum 코드만 저장합니다. 원시 예외 메시지,
외부 제공자 응답, API 키 등 내부 정보는 응답에 포함하지 않습니다. 앱은 코드를 고정된
사용자 안내 문구로 변환하며, 재시도는 같은 입력으로 새 추천 요청을 만듭니다.

---

## POST /routes/{routeId}/edit-suggestions

완성된 추천 루트에서 자연어로 교체 후보를 요청합니다.

```json
{
  "targetItemId": "교체 버튼을 누른 routeItemId",
  "instruction": "숙소에서 가까운 조용한 카페로 바꿔줘"
}
```

루트 수정 전용 LLM은 선택된 일정 항목을 대상으로 원하는 조건만 해석합니다. 실제 후보는
일반 챗봇이 아니라 기존 DB 하드 필터와 요청 당시의 `applied_weights`로 다시 계산합니다.
응답의 `suggestions`에는 현재 일정과 겹치지 않는 상위 3개 장소가 담기며, 이 요청만으로
일정은 변경되지 않습니다.

후보를 고른 뒤에는 직접 장소를 선택했을 때와 동일하게
`PUT /route-items/{routeItemId}/place`를 호출합니다.

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
      "creationType": "recommended",
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
  "creationType": "recommended",
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
    { "id": "...", "name": "몽이", "species": "dog", "speciesDetail": null, "size": "small" }
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
| `creationType` | `recommended` \| `manual`. `manual`이면 `pets`가 `route_pets` 기준이고 재생성이 불가합니다 |
| `place` | `place_id`가 있을 때. 직접 입력한 장소면 `null`이고 `customPlaceName`에 이름이 들어감 |
| `moveToNext` | 마지막 항목이면 `null`. `route_moves` + TMAP 계산 결과 |
| `distanceMeters` `durationMinutes` | **DB에 영구 저장하지 않습니다.** `route_calculation_cache`에 최대 24시간만 캐시하고 만료되면 다시 계산합니다 |
| `weather` | `route_days.weather_snapshot_id` 조인. 없으면 `null` |
| `stays` | 추천 요청의 `route_request_stays`. 수동 여행이면 빈 배열 |
| `isSelected` | 추천 항목 중 사용자가 뺀 것을 구분. 기본 `true` |
| `distanceSummary` | 계산값. 하위 `moveToNext` 합계 |
| `tourApiPlaces` | 상세 조회 시 한국관광공사 TourAPI에서 실시간 조회한 주변 장소 최대 3건. DB에 저장하지 않음 |
| `logCount` | 계산값. 이 여행에 속한 `travel_logs` 개수. 여행 모아보기 화면 헤더가 씀 ([`travel-logs.md`](./travel-logs.md)) |

`route_moves`에는 순서와 이동수단만 영구 저장하고, 거리·시간·polyline은 캐시에서 가져옵니다.

날씨는 루트 생성 시 저장된 스냅샷만 반환합니다. 상세 조회 시 기상청 API를 다시
호출하지 않으므로 기상청 장애나 API 키 누락이 있어도 상세 응답은 정상 반환되며,
저장된 스냅샷이 없는 날짜의 `weather`는 `null`입니다.

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

이 엔드포인트는 `creationType`이 `recommended`인 여행에만 씁니다.
수동 여행은 `routeRequestId`가 `null`이라 재생성할 원본 조건이 없습니다.

**수동 여행에 호출하면 `422`입니다.** **[확정]** (2026-08-18)

다른 엔드포인트들이 상태 위반에 이미 `422`를 쓰고 있어 맞췄습니다.

```json
{ "detail": "직접 만든 여행은 다시 추천받을 수 없어요" }
```

앱에서는 애초에 **수동 여행에 이 버튼을 보여주지 않는 것이 정상 동작**입니다.
응답의 `creationType`으로 구분할 수 있습니다. 이 `422`는 만일을 대비한 방어입니다.

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
DB 장소를 추가하면 좌표와 기본 체류시간을 함께 스냅샷으로 저장합니다. `startsAt`만
보내고 `endsAt`을 생략하면 기본 체류시간을 더해 종료 시각을 계산합니다.

앱의 `PlaceCategory`는 `etc`를 쓰지만 DB `schedule_item_type`은 `custom`입니다.
**API는 `custom`을 씁니다.**

### PATCH /route-items/{routeItemId}

시각·체류시간·메모·`isSelected`를 수정합니다. `sortOrder` 변경은 아래 순서 API를 씁니다.

`endsAt`은 `startsAt`보다 뒤여야 하고, `stayMinutes`는 0 이상입니다.

### PUT /route-items/{routeItemId}/place

AI 추천 후보 또는 사용자가 직접 고른 DB 장소로 일정 항목을 교체합니다.

```json
{ "placeId": "550e8400-e29b-41d4-a716-446655440000" }
```

서버는 요청 당시의 반려동물·영업 조건을 다시 검사하고 추천 점수와 루트 종합 점수를
갱신합니다. 같은 루트에 이미 있는 장소이거나 하드 필터를 통과하지 못한 장소는
`422`로 거절합니다. 교체 항목 앞뒤의 TMAP 경로는 다시 계산해 캐시에 저장합니다.
숙소 항목은 숙소 후보로만 교체할 수 있으며, 숙박일의 도착 숙소와 다음 날 출발 숙소는
같은 장소로 함께 변경됩니다.

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
| 2026-08-15 | PR #29 머지 반영 — 수동 여행 스키마(`creation_type`, nullable `route_request_id`, `route_pets`) 설명 추가, 응답에 `creationType` 추가, `regenerate`의 수동 여행 처리 명시. 수동 생성 엔드포인트는 확인 필요로 기록 |
| 2026-08-18 | 미정 2건 확정 — 폴링 **2초 간격 / 3분 타임아웃**, `failureReason`은 컬럼 추가 없이 응답에만, 수동 여행 재생성은 **`422`**. 수동 생성 엔드포인트는 **보류 유지**하되 DB 준비 완료 사실과 유력안을 정리 |
| 2026-08-30 | 생성 실패를 재시도·운영 분석에 활용할 수 있도록 `failureReason`을 `routes.failure_reason`의 안전한 enum 코드로 저장하도록 변경 |
