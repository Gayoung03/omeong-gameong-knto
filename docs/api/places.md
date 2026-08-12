# 장소 · 즐겨찾기 API

작성일: 2026-08-12 · 상태: **확정 규약 반영** (2026-08-12 팀 회의)

공통 규약은 [`README.md`](./README.md)를 따릅니다.

관련 DB 테이블: `places`, `place_business_hours`, `place_pet_policies`, `place_tags`,
`place_tag_links`, `place_external_refs`, `favorites`

---

## 엔드포인트 목록

| Method | Path | 설명 | 인증 |
| --- | --- | --- | --- |
| GET | `/places` | 장소 목록·검색 | 선택 |
| GET | `/places/{placeId}` | 장소 상세 | 선택 |
| POST | `/places` | 나만의 장소 등록 **[확인 필요]** | 필요 |
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
| `limit` | int | 20 | 최대 100 |
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

> **[확인 필요]** 앱의 `Place` 타입은 `petFriendly: boolean` 한 개로 되어 있는데
> DB는 5종 enum입니다. 이 문서는 5종을 그대로 내리는 쪽으로 작성했습니다.
> 장소 카드 UI에서 5종을 어떻게 표시할지(특히 `unknown`) 디자인 확인이 필요합니다.

> **[확인 필요] — 사용자 등록 장소의 노출 범위. 정하지 않으면 사고가 납니다.**
>
> 사용자가 직접 등록한 "나만의 장소"는 별도 테이블이 아니라 **`places`에 함께 저장**됩니다
> (`created_by_user_id`를 채움, [DB 문서](../database/README.md) 참고).
> 그런데 이 문서에는 `GET /places`가 그것들을 어떻게 다루는지 규칙이 없습니다.
>
> **아무 조건도 걸지 않으면 남이 등록한 장소가 전체 검색 결과에 그대로 노출됩니다.**
> 이름("우리 강아지 단골 카페")과 좌표가 함께 나가므로 개인정보 문제로 이어질 수 있습니다.
>
> 선택지는 두 가지입니다. 둘 다 **남의 장소는 보이지 않는다**는 점은 같고,
> 내 장소가 일반 검색에 섞이는지 아닌지가 다릅니다.
>
> | 안 | 내용 |
> | --- | --- |
> | A | 공식 장소 + 내가 등록한 장소를 함께 반환 |
> | B | 기본은 공식 장소만. `?includeMine=true` 같은 파라미터로만 내 장소 포함 |
>
> 앱의 일정 추가 화면에는 **`나만의 장소` 탭이 따로** 있습니다
> ([`placeSearch.ts:31`](../../apps/mobile/src/features/trips/constants/placeSearch.ts)).
> 목록을 별도로 부르는 구조라 B가 화면과 더 잘 맞지만, **확정된 것은 아닙니다.**
>
> 정해지기 전까지 이 문서의 `GET /places` 응답 예시는 공식 장소만 가정합니다.

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
  "activityLevel": 3,
  "crowdLevel": 4,
  "weatherSensitivity": 5,
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
- `activityLevel` `crowdLevel` `weatherSensitivity` — 1~5. 추천 알고리즘 입력값입니다.
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

> **[확인 필요] — 앱에 등록 화면이 없습니다.**
>
> 등록된 장소를 **보여주는** 곳은 있습니다. 일정 추가 화면의 `나만의 장소` 탭
> ([`placeSearch.ts:31`](../../apps/mobile/src/features/trips/constants/placeSearch.ts))이고,
> 비었을 때 문구("직접 등록한 장소가 없어요")와 목업 데이터까지 준비되어 있습니다.
>
> 그런데 **장소를 만드는 화면이나 버튼이 앱에 없습니다.** 저장소 전체를 확인했습니다.
> 지금 상태로는 이 탭이 영원히 비어 있게 됩니다.
>
> | | 상태 |
> | --- | --- |
> | 조회 (`나만의 장소` 탭) | 있음 |
> | 등록 화면·진입점 | **없음** |
> | DB 컬럼 (`created_by_user_id`) | 있음 |
> | API 명세 (이 절) | 있음 |
>
> 아래 요청·응답은 **DB 컬럼을 근거로 미리 작성해 둔 것**이며,
> 화면 기획이 나오면 필드가 달라질 수 있습니다.
> 등록 기능을 이번 범위에 넣을지부터 정해야 합니다.
>
> 수정·삭제 엔드포인트도 아직 없습니다. 잘못 등록하면 되돌릴 방법이 없습니다.

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

> **[확인 필요]** 태그 목록이 확정되지 않았습니다.
> 앱의 취향 선택지(`자연` `실내` `카페` `산책` `사진` `조용한` `활동적`)와
> DB 설계 문서의 태그(`바다` `카페` `산책` `포토스팟` `체험` `휴식` `실내관광`)가 다릅니다.
> 이 태그는 추천 알고리즘 입력값이라 장소 데이터에 다시 붙여야 하므로 되돌리기 비쌉니다.

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
