# 장소 · 즐겨찾기 API

작성일: 2026-08-12 · 갱신: 2026-08-18 · 상태: **장소 태그 목록만 보류 — 그 외 구현 착수 가능**

공통 규약은 [`README.md`](./README.md)를 따릅니다.

관련 DB 테이블: `places`, `place_business_hours`, `place_pet_policies`, `place_tags`,
`place_tag_links`, `place_external_refs`, `favorites`

---

## 엔드포인트 목록

| Method | Path | 설명 | 인증 |
| --- | --- | --- | --- |
| GET | `/places` | 공식 장소 목록·검색 | 선택 |
| GET | `/places/{placeId}` | 장소 상세 | 선택 |
| POST | `/places` | 나만의 장소 등록 | 필요 |
| GET | `/users/me/places` | 내가 등록한 장소 목록 | 필요 |
| GET | `/place-tags` | 태그 목록 | — |
| GET | `/users/me/favorites` | 내 즐겨찾기 목록 | 필요 |
| PUT | `/places/{placeId}/favorite` | 즐겨찾기 등록 | 필요 |
| DELETE | `/places/{placeId}/favorite` | 즐겨찾기 해제 | 필요 |

**인증 "선택"** — 비로그인도 조회할 수 있지만, 토큰이 있으면 응답에 `isFavorite`가 포함됩니다.
토큰이 없으면 이 필드는 항상 `false`입니다.

---

## GET /places

목록·검색·주변 조회를 한 엔드포인트로 처리합니다.

### 요청

```text
GET /api/v1/places?q=함덕&category=beach&limit=20&offset=0
GET /api/v1/places?latitude=33.4996&longitude=126.5312&radius=3000
```

| 파라미터 | 타입 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `q` | string | — | 장소명 검색어 |
| `category` | string | — | `places.category` |
| `region` | string | — | `places.region` |
| `tags` | string[] | — | `place_tags.code`. 여러 개면 AND |
| `petPolicy` | enum[] | — | `indoor_allowed` `outdoor_only` `partial_allowed` `not_allowed` `unknown` |
| `environment` | enum | — | `indoor` `outdoor` `mixed` |
| `latitude` | number | — | -90 ~ 90 |
| `longitude` | number | — | -180 ~ 180 |
| `radius` | int | 3000 | 미터. 좌표를 보낼 때만 유효 |
| `sort` | enum | `distance` 또는 `name` | `distance` `name` `reviewCount` |
| `limit` | int | 20 | 최대 1000 |
| `offset` | int | 0 | |

좌표를 보내면 기본 정렬이 `distance`, 없으면 `name`입니다.

좌표는 **DB에 저장하지 않습니다.** 계산에만 쓰고 로그에 남길 때 마스킹합니다
([DB 문서](../database/README.md)의 GPS 정책).

### 응답 `200`

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "함덕해수욕장",
      "category": "beach",
      "region": "함덕/김녕/세화",
      "address": "제주특별자치도 제주시 조천읍 함덕리 1004",
      "roadAddress": "제주특별자치도 제주시 조천읍 조함해안로 525",
      "latitude": 33.5432,
      "longitude": 126.6695,
      "primaryImageUrl": "https://...",
      "environment": "outdoor",
      "petPolicyType": "outdoor_only",
      "tags": ["바다", "산책"],
      "reservationRequired": false,
      "distanceMeters": 4820,
      "reviewCount": 37,
      "savedCount": 128,
      "rating": 4.3,
      "isFavorite": true
    }
  ],
  "total": 137,
  "limit": 20,
  "offset": 0
}
```

목록에는 요약 정보만 담습니다. 영업시간·상세 정책은 상세 조회에서 내려줍니다.

| 필드 | 출처 |
| --- | --- |
| `distanceMeters` | 계산값. 좌표를 보내지 않으면 `null` |
| `reviewCount` `savedCount` `rating` | 계산값 (`reviews`, `favorites` 집계) |
| `isFavorite` | 계산값. 비로그인이면 `false` |
| `petPolicyType` | `place_pet_policies.policy_type` |
| `tags` | `place_tag_links` → `place_tags.code` |

### 사용자 등록 장소는 여기에 나오지 않습니다 **[확정]** (2026-08-18)

사용자가 직접 등록한 "나만의 장소"는 별도 테이블이 아니라 **`places`에 함께 저장**됩니다
(`created_by_user_id`를 채움, [DB 문서](../database/README.md) 참고).
그래서 조건을 걸지 않으면 남이 등록한 장소가 전체 검색 결과에 섞여 나옵니다.
이름("우리 강아지 단골 카페")과 좌표가 함께 나가므로 개인정보 문제가 됩니다.

**완전 분리로 확정했습니다.**

```sql
-- GET /places 는 항상 이 조건이 붙습니다
WHERE created_by_user_id IS NULL
```

| 조회 경로 | 나오는 것 |
| --- | --- |
| `GET /places` | 공식 장소만 |
| `GET /users/me/places` | 내가 등록한 장소만 |
| **남이 등록한 장소** | **어떤 경로로도 나오지 않음** |

`?includeMine=true` 같은 파라미터로 섞어서 보여주는 방식은 쓰지 않습니다.
조건을 빠뜨리면 그대로 사고가 나는 구조라, **아예 섞일 수 없게** 경로를 나눴습니다.

앱의 일정 추가 화면도 `나만의 장소` 탭이 따로 있어
([`placeSearch.ts:31`](../../apps/mobile/src/features/trips/constants/placeSearch.ts))
목록을 별도로 부르는 이 구조와 맞습니다.

`GET /places/{placeId}` 상세 조회도 같습니다. 남의 장소 ID로 직접 요청하면 `404`입니다.

### `petPolicyType`은 5종을 그대로 내립니다 **[확정]** (2026-08-18)

앱의 `Place` 타입은 `petFriendly: boolean` 한 개인데 DB는 5종 enum입니다.
**5종을 그대로 내리고 앱이 뱃지로 표시합니다.** `petFriendly` boolean은 쓰지 않습니다.

`unknown`은 **회색 "정보 없음" 뱃지**로 표시합니다. 뱃지를 아예 안 그리면 카드 높이가
들쭉날쭉해지고, 정보가 없다는 사실을 사용자가 알 수 없습니다.

> **앱 반영 완료 (2026-08-18, PR #37).** [`PetPolicyBadge.tsx`](../../apps/mobile/src/components/domain/PetPolicyBadge.tsx)의
> `BADGE_COLORS`에 `unknown`(회색)을 추가했고, `PetPolicy` 타입도 5종으로 맞췄습니다.
> 정본은 [`src/types/place.ts`](../../apps/mobile/src/types/place.ts)로 옮겨졌습니다 —
> 장소 탐색에서도 같은 배지를 쓰게 되어 `src/components/domain/`으로 승격했습니다.

---

## GET /places/{placeId}

### 응답 `200`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "함덕해수욕장",
  "category": "beach",
  "region": "함덕/김녕/세화",
  "address": "제주특별자치도 제주시 조천읍 함덕리 1004",
  "roadAddress": "제주특별자치도 제주시 조천읍 조함해안로 525",
  "latitude": 33.5432,
  "longitude": 126.6695,
  "phone": "064-728-3989",
  "homepageUrl": "https://...",
  "primaryImageUrl": "https://...",
  "description": "제주 동부를 대표하는 에메랄드빛 해수욕장입니다.",
  "descriptionSource": "visitjeju",
  "environment": "outdoor",
  "amenities": ["주차장", "화장실", "편의점"],
  "averageStayMinutes": 90,
  "reservationRequired": false,
  "isUserCreated": false,
  "tags": [
    { "code": "바다", "name": "바다" },
    { "code": "산책", "name": "산책" }
  ],
  "petPolicy": {
    "policyType": "outdoor_only",
    "allowedSpecies": ["dog", "cat"],
    "allowedSizes": ["small", "medium"],
    "maxWeightKg": 15.0,
    "carrierRequired": false,
    "leashRequired": true,
    "vaccinationRequired": null,
    "extraFeeAmount": 0,
    "notes": "해변 산책로만 동반 가능합니다.",
    "source": "tour_api",
    "sourceUrl": "https://...",
    "verifiedAt": "2026-07-20T10:00:00+09:00",
    "reliabilityScore": 82.5
  },
  "businessHours": [
    {
      "dayOfWeek": 0,
      "opensAt": "09:00:00",
      "closesAt": "18:00:00",
      "breakStartAt": null,
      "breakEndAt": null,
      "isClosed": false,
      "rawText": "09:00~18:00"
    }
  ],
  "reviewCount": 37,
  "savedCount": 128,
  "rating": 4.3,
  "isFavorite": true
}
```

### 주의할 필드

- `dayOfWeek` — 0(일요일) ~ 6(토요일). DB CHECK 제약과 동일합니다.
- `petPolicy` — 정책 정보가 없는 장소는 `policyType`이 `unknown`이고 나머지는 대부분 `null`입니다.
- `reliabilityScore` — 0~100. 정책 정보의 신뢰도로, 출처와 확인 시점에 따라 달라집니다.
- `isUserCreated` — `created_by_user_id`가 있으면 `true`. 사용자 ID 자체는 노출하지 않습니다.

`place_external_refs`(제공처 원본 ID)는 내부 동기화용이라 응답에 포함하지 않습니다.

### 에러

| 코드 | 상황 |
| --- | --- |
| 404 | 없는 `placeId` 또는 `is_active = false` |

---

## POST /places

사용자가 직접 등록하는 "나만의 장소"입니다.
별도 테이블을 만들지 않고 `places`에 저장하며, `created_by_user_id`를 채웁니다
([DB 문서](../database/README.md) 참고).

**등록 기능은 이번 범위에 포함합니다** (2026-08-18 확정).

등록된 장소를 **보여주는** 곳은 이미 있습니다. 일정 추가 화면의 `나만의 장소` 탭
([`placeSearch.ts:31`](../../apps/mobile/src/features/trips/constants/placeSearch.ts))이고,
비었을 때 문구("직접 등록한 장소가 없어요")와 목업 데이터까지 준비되어 있습니다.

> **앱 수정 필요.** 장소를 **만드는** 화면과 진입점이 아직 없습니다.
> 지금 상태로는 `나만의 장소` 탭이 계속 비어 있습니다.
>
> | | 상태 |
> | --- | --- |
> | 조회 (`나만의 장소` 탭) | 있음 |
> | 등록 화면·진입점 | **없음 — 제작 예정** |
> | DB 컬럼 (`created_by_user_id`) | 있음 |
> | API 명세 (이 절) | 있음 |
>
> 아래 요청·응답은 DB 컬럼을 근거로 작성했습니다.
> 등록 화면이 나오면 필드가 조정될 수 있습니다.

수정·삭제 엔드포인트는 아직 없습니다. 등록 화면과 함께 정하면 됩니다.

### 요청

```json
{
  "name": "우리 강아지 단골 카페",
  "category": "cafe",
  "address": "제주특별자치도 제주시 ...",
  "latitude": 33.4996,
  "longitude": 126.5312,
  "primaryImageUrl": "https://...",
  "description": "실내 동반 가능하고 조용합니다."
}
```

| 필드 | 필수 | 제약 |
| --- | --- | --- |
| `name` | ✅ | 200자 |
| `category` | ✅ | 50자 |
| `latitude` | ✅ | -90 ~ 90 |
| `longitude` | ✅ | -180 ~ 180 |

`descriptionSource`는 서버가 `internal`로 설정합니다.

`primaryImageUrl`은 [`uploads.md`](./uploads.md)의 `POST /uploads`로 먼저 받습니다
(`purpose`는 `place`).

### 응답 `201`

`GET /places/{placeId}` 와 동일한 구조입니다.

### 에러

| 코드 | 상황 |
| --- | --- |
| 422 | 좌표 범위 초과, 필수 필드 누락 |

---

## GET /users/me/places

내가 등록한 장소만 돌려줍니다. 일정 추가 화면의 `나만의 장소` 탭이 이걸 부릅니다.

`GET /places`가 공식 장소만 다루므로(위 [완전 분리](#사용자-등록-장소는-여기에-나오지-않습니다-확정-2026-08-18) 참고)
내 장소를 보려면 이 경로를 써야 합니다.

### 요청

```text
GET /api/v1/users/me/places?q=카페&limit=20&offset=0
```

| 파라미터 | 타입 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `q` | string | — | 장소명 검색어 |
| `limit` | int | 20 | 최대 100 |
| `offset` | int | 0 | |

### 응답 `200`

`GET /places`와 같은 항목 구조입니다. 다만 아래가 다릅니다.

| 필드 | 값 |
| --- | --- |
| `tags` | 항상 `[]`. 태그는 서버가 공식 장소에만 붙입니다 |
| `reviewCount` `rating` | 항상 `0` / `null`. 내 장소에는 리뷰를 쓸 수 없습니다 |
| `distanceMeters` | 항상 `null`. 좌표 파라미터를 받지 않습니다 |

`created_by_user_id`가 토큰의 사용자와 다른 행은 조회되지 않습니다.

---

## GET /place-tags

취향 선택·필터에 쓸 태그 목록입니다.

### 응답 `200`

```json
{
  "items": [
    { "code": "바다", "name": "바다" },
    { "code": "카페", "name": "카페" }
  ],
  "total": 7,
  "limit": 20,
  "offset": 0
}
```

`code`는 [`README.md`](./README.md) 7장 규약대로 **영문 코드**입니다.
`name`이 화면에 보일 한글 이름입니다. 위 예시의 `code`가 한글인 것은 목록 미확정 때문이며,
확정되면 `{ "code": "sea", "name": "바다" }` 형태가 됩니다.

> **[확인 필요] — 태그 목록 자체는 아직 보류입니다.** (2026-08-18 갱신)
>
> 장소 태그(`place_tags`)와 사용자 취향(`user_travel_preferences.preferred_tags`)은
> **역할이 다른 별개의 목록**입니다.
>
> | | 채우는 주체 | 용도 |
> | --- | --- | --- |
> | 장소 태그 | 서버·데이터 제공처가 자동 부여 (`place_tag_links.confidence`, `source`) | 장소의 특징 |
> | 사용자 취향 | 사용자가 회원가입에서 선택 ([`users.md`](./users.md)) | 내 선호 |
>
> **두 목록의 단어를 맞출지는 추천 방식이 정해져야 답이 나옵니다.**
>
> - **규칙 기반** (취향 단어와 장소 태그를 직접 대조) → 두 목록의 단어를 **반드시 통일**해야 함.
>   지금처럼 취향은 `자연`, 장소는 `바다`면 자연을 고른 사용자에게 해변이 추천되지 않습니다
> - **AI 기반** (`app/rag/`) → 단어가 달라도 문맥으로 이해하므로 통일 불필요
>
> 저장소에 `app/rag/{ingestion,prompts,retrieval}` 골격이 잡혀 있어 AI 방식으로 보이지만
> **확정된 적이 없습니다.** 추천 방식이 정해질 때 이 항목을 다시 봐야 합니다.
>
> 태그는 장소 데이터에 다시 붙여야 해서 되돌리기 비쌉니다.

---

## GET /users/me/favorites

### 요청

```text
GET /api/v1/users/me/favorites?limit=20&offset=0
```

### 응답 `200`

`GET /places`와 같은 항목 구조에 `favoritedAt`이 추가됩니다.

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "함덕해수욕장",
      "category": "beach",
      "primaryImageUrl": "https://...",
      "petPolicyType": "outdoor_only",
      "isFavorite": true,
      "favoritedAt": "2026-08-01T14:00:00+09:00"
    }
  ],
  "total": 12,
  "limit": 20,
  "offset": 0
}
```

기본 정렬은 `favoritedAt` 최신순입니다.

---

## PUT /places/{placeId}/favorite

즐겨찾기에 넣습니다. `POST`가 아니라 `PUT`인 이유는 **여러 번 눌러도 결과가 같아야** 하기 때문입니다.
`favorites` 테이블의 기본키가 `(user_id, place_id)`라 중복 행이 생길 수 없습니다.

### 요청

본문 없음.

### 응답 `204`

본문 없음. 이미 즐겨찾기한 장소여도 `204`입니다(409 아님).

### 에러

| 코드 | 상황 |
| --- | --- |
| 404 | 없는 `placeId` |

---

## DELETE /places/{placeId}/favorite

### 응답 `204`

본문 없음. 즐겨찾기하지 않은 장소여도 `204`입니다.

### 에러

| 코드 | 상황 |
| --- | --- |
| 404 | 없는 `placeId` |

---

## 변경 이력

| 날짜 | 내용 |
| --- | --- |
| 2026-08-12 | 초안 작성 |
| 2026-08-12 | `primaryImageUrl` 업로드 경로를 [`uploads.md`](./uploads.md) 참조로 명시 |
| 2026-08-12 | 사용자 등록 장소의 노출 규칙 부재를 확인 필요로 기록. 앱에 등록 화면이 없다는 사실도 함께 남김 |
| 2026-08-15 | PR #29 머지 반영 — `activityLevel` `crowdLevel` `weatherSensitivity` 삭제. 마이그레이션 `8c71f4a2d9e0`에서 `places` 컬럼이 drop되어 응답에서 제거 |
| 2026-08-18 | 미정 3건 확정 — 사용자 등록 장소 **완전 분리**(`GET /users/me/places` 신설), 등록 화면 **제작 확정**, `petPolicyType` 5종 유지 및 `unknown`은 회색 "정보 없음" 뱃지. 태그 목록은 보류 사유를 "추천 방식 미확정"으로 정정 |
