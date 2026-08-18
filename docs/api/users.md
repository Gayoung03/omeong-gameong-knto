# 사용자 · 반려동물 API

작성일: 2026-08-12 · 갱신: 2026-08-18 · 상태: **취향 태그 목록만 보류 — 그 외 구현 착수 가능**

공통 규약은 [`README.md`](./README.md)를 따릅니다. 이 문서에 적용된 확정 사항은 다음과 같습니다.

| # | 확정 내용 | 이 문서에서 |
| --- | --- | --- |
| 2 | 응답 필드는 camelCase | 모든 예시 |
| 3 | 반려동물 종류는 강아지 / 고양이 / 기타 | 반려동물 등록·수정 |
| 4 | 나이는 서버가 `birthDate`로 계산 | `GET /pets` |
| 5 | Soft delete는 `status: active \| deleted` | 반려동물·사용자 응답 |
| 9 | 목록은 `{ items, total, limit, offset }` | `GET /pets` |

관련 DB 테이블: `users`, `pets`, `user_travel_preferences`
반려동물 soft delete 정책은 [`docs/database/pets-soft-delete.md`](../database/pets-soft-delete.md) 참고.

---

## "기타" 종류 입력값 — `speciesDetail`

"기타"를 선택했을 때 사용자가 직접 입력한 텍스트는 `pets.species_detail`에 저장합니다.
API에서는 camelCase 규약에 따라 **`speciesDetail`** 로 주고받습니다.

마이그레이션 `8c71f4a2d9e0`에서 추가됐습니다 (`VARCHAR(50)`, nullable).

`breed`와 용도가 다릅니다. `breed`는 **품종**(말티즈·푸들), `speciesDetail`은 **종류**(햄스터·앵무새)입니다.
품종 칸에 "햄스터"를 넣으면 나중에 품종 기반 기능을 만들 때 데이터가 섞입니다.

DB에 CHECK 제약(`species_detail_consistency`)이 걸려 있어 아래 두 경우만 저장됩니다.

| `species` | `speciesDetail` |
| --- | --- |
| `other` | 필수. 공백만 있는 문자열도 거부 |
| `other` 외 | 반드시 `null` |

`dog`인데 `speciesDetail`에 값을 보내면 DB 제약에 걸리므로, 서버가 422로 먼저 막아야 합니다.

`rabbit` `bird`는 enum에 남아 있지만 앱 선택지에서 제공하지 않습니다.
기존 데이터가 없으므로 enum 자체를 줄이는 선택지도 있습니다 — 이건 별도 논의가 필요합니다.

---

## 엔드포인트 목록

| Method | Path | 설명 | 인증 |
| --- | --- | --- | --- |
| GET | `/users/me` | 내 정보 조회 | 필요 |
| PATCH | `/users/me` | 닉네임·프로필 이미지 수정 | 필요 |
| DELETE | `/users/me` | 회원 탈퇴 | 필요 |
| PATCH | `/users/me/notification-preferences` | 알림 수신 설정 | 필요 |
| GET | `/users/me/travel-preference` | 기본 여행 취향 조회 | 필요 |
| PUT | `/users/me/travel-preference` | 기본 여행 취향 수정 | 필요 |
| GET | `/pets` | 내 반려동물 목록 | 필요 |
| POST | `/pets` | 반려동물 등록 | 필요 |
| GET | `/pets/{petId}` | 반려동물 상세 | 필요 |
| PATCH | `/pets/{petId}` | 반려동물 수정 | 필요 |
| DELETE | `/pets/{petId}` | 반려동물 삭제 (soft) | 필요 |

---

## GET /users/me

### 응답 `200`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "traveler@example.com",
  "nickname": "여행자",
  "profileImageUrl": "https://...",
  "authProvider": "local",
  "status": "active",
  "notificationPreferences": {
    "inquiryAnswerEnabled": true,
    "marketingEnabled": false
  },
  "activitySummary": {
    "savedPlacesCount": 12,
    "savedRoutesCount": 3,
    "travelLogsCount": 27
  },
  "createdAt": "2026-03-01T09:00:00+09:00"
}
```

`activitySummary`의 세 값은 **DB에 저장하지 않고 조회 시 계산**합니다
(`favorites`, `routes`, `travel_logs` 카운트). DB 설계 문서에서 중복 저장하지 않기로 한 값입니다.

`notificationPreferences`는 `users` 테이블의 두 컬럼
(`inquiry_answer_notification_enabled`, `marketing_notification_enabled`)을 묶어서 내려줍니다.
앱의 [`types/notification.ts`](../../apps/mobile/src/types/notification.ts)가 이미 이 구조입니다.

---

## PATCH /users/me

닉네임과 프로필 이미지만 수정합니다. 이메일과 `authProvider`는 변경 불가입니다.

### 요청

```json
{
  "nickname": "제주여행자",
  "profileImageUrl": "https://..."
}
```

두 필드 모두 선택입니다. 보낸 필드만 수정합니다.
`profileImageUrl`을 `null`로 보내면 기본 이미지로 되돌립니다.

새 이미지를 쓸 때는 [`uploads.md`](./uploads.md)의 `POST /uploads`로 먼저 주소를 받습니다
(`purpose`는 `profile`).

### 응답 `200`

`GET /users/me` 와 동일한 구조입니다.

### 에러

| 코드 | 상황 |
| --- | --- |
| 422 | 닉네임 길이 초과 (50자) |

---

## DELETE /users/me

회원 탈퇴입니다. 물리 삭제가 아니라 `users.deleted_at`을 기록해 `status`를 `deleted`로 바꿉니다.

### 요청

```json
{ "password": "********" }
```

| 필드 | 필수 | 설명 |
| --- | --- | --- |
| `password` | 조건부 | `authProvider`가 `local`일 때만 필수 |
| `providerAccessToken` | 조건부 | 소셜 계정일 때 필수 |

소셜 계정은 비밀번호가 없으므로, 앱이 제공처 재인증을 먼저 수행하고 그 토큰을 보냅니다
([`accountService.ts:21`](../../apps/mobile/src/features/auth/services/accountService.ts) 주석 기준).

```json
{ "providerAccessToken": "..." }
```

### 응답 `204`

본문 없음. 앱은 저장된 토큰과 로컬 데이터를 정리합니다.

### 에러

| 코드 | 상황 |
| --- | --- |
| 401 | 비밀번호 불일치 또는 재인증 실패 |

**같은 이메일로 재가입 [확정]** — 차단합니다. (2026-08-15)

탈퇴한 계정의 이메일로 `POST /auth/signup`을 호출하면 `409`이고,
`GET /auth/check-email`은 `available: false`입니다.
탈퇴가 soft delete라 행이 남고 `users.email`에 UNIQUE가 걸려 있어 이미 그렇게 동작합니다.
근거와 나중에 여는 방법은 [`auth.md`](./auth.md) 참고.

**보관 기간 [확정]** — **30일**입니다. (2026-08-18)

```text
탈퇴 ──── 30일 ────▶ 이메일 익명화 ────▶ 같은 이메일로 재가입 가능
      재가입 차단                    차단 해제
```

탈퇴 후 30일이 지난 행은 배치가 `users.email`을 익명값으로 바꿉니다.
UNIQUE 제약이 풀리는 시점이라 그때부터 같은 이메일로 재가입할 수 있습니다.

30일로 정한 이유는 두 가지입니다. 실수로 탈퇴한 사용자가 문의할 시간이 되고,
그 이상 개인정보를 들고 있을 이유가 없습니다.

닉네임도 함께 익명화합니다. 리뷰는 남지만 작성자 표시가 "탈퇴한 사용자"로 바뀌므로
([`reviews.md`](./reviews.md)) 화면에는 영향이 없습니다.

탈퇴해도 `travel_log_pets`의 이름·사진 스냅샷은 남으므로 다른 사용자의 기록 화면은 영향받지 않습니다.

---

## PATCH /users/me/notification-preferences

### 요청

```json
{
  "inquiryAnswerEnabled": true,
  "marketingEnabled": false
}
```

두 필드 모두 선택입니다.

### 응답 `200`

```json
{
  "inquiryAnswerEnabled": true,
  "marketingEnabled": false
}
```

---

## GET /users/me/travel-preference

회원가입 때 입력한 평소 여행 취향입니다.
**이번 여행 조건(`route_requests`)과는 별개**이며, 추천 시 우선순위는 아래와 같습니다.

```text
이번 여행에서 직접 입력한 값 > 사용자 기본 취향 > 서비스 기본값
```

### 응답 `200`

```json
{
  "defaultPace": "relaxed",
  "defaultTransport": "rental_car",
  "departureLocation": "제주시",
  "preferredDurationDays": 2,
  "companionCount": 1,
  "preferredTags": ["nature", "cafe", "walk"],
  "updatedAt": "2026-08-01T10:00:00+09:00"
}
```

enum 값은 영문 코드 그대로입니다. `rental_car`의 값 자체에 있는 밑줄은 표기법이 아니라
**값의 일부**이므로 camelCase로 바꾸지 않습니다. 필드명만 camelCase입니다.

가입 시 취향을 건너뛴 사용자는 대부분 `null`이고 `companionCount`만 `1`입니다.

---

## PUT /users/me/travel-preference

전체를 덮어씁니다. 취향 설정 화면이 항상 전체 폼을 제출하기 때문에 `PATCH`가 아닌 `PUT`입니다.

### 요청

```json
{
  "defaultPace": "normal",
  "defaultTransport": "own_car",
  "departureLocation": "서귀포시",
  "preferredDurationDays": 3,
  "companionCount": 2,
  "preferredTags": ["photo", "quiet"]
}
```

| 필드 | 타입 | 제약 |
| --- | --- | --- |
| `defaultPace` | enum | `relaxed` `normal` `packed` |
| `defaultTransport` | enum | `rental_car` `own_car` `taxi` `public_transport` `walk` `ferry` `airplane` |
| `preferredDurationDays` | int | 1 이상 |
| `companionCount` | int | 1 이상 |
| `preferredTags` | string[] | 아래 취향 태그 코드 |

### 에러

| 코드 | 상황 |
| --- | --- |
| 422 | `companionCount < 1`, `preferredDurationDays < 1` |

### 취향 태그 코드 **[확정]** (2026-08-18)

`preferredTags`에는 **영문 코드**를 넣습니다. 화면에 보일 한글은 앱이 라벨로 바꿉니다
([`README.md`](./README.md) 7장 규약).

| 화면 표시 | 코드 |
| --- | --- |
| 자연 | `nature` |
| 실내 | `indoor` |
| 카페 | `cafe` |
| 산책 | `walk` |
| 사진 | `photo` |
| 조용한 | `quiet` |
| 활동적 | `active` |

> **앱 수정 필요.** [`signupOptions.ts`](../../apps/mobile/src/features/auth/constants/signupOptions.ts)의
> `vibeOptions`가 지금 `{ value: '자연' }`처럼 한글을 값으로 쓰고 있습니다.
> 같은 파일의 `petTypeOptions`처럼 `{ value: 'nature', label: '자연' }` 형태로 바꿔야 합니다.

> **[확인 필요] — 목록 자체는 아직 보류입니다.**
> 위 7개는 **현재 앱 화면에 있는 선택지를 코드로 옮긴 것**입니다.
> 이 목록이 장소 태그(`place_tags`)와 단어를 맞춰야 하는지는
> **추천 방식(규칙 기반 / AI)이 정해져야** 답이 나옵니다.
> 자세한 내용은 [`places.md`](./places.md)의 `GET /place-tags` 절에 있습니다.

`preferredTags`는 `user_travel_preferences.preferred_tags`(문자열 배열)에 그대로 저장됩니다.
`place_tags` 테이블의 외래키가 아니라서 목록이 바뀌어도 DB 제약에 걸리지 않습니다.

---

## GET /pets

### 요청

```text
GET /api/v1/pets
GET /api/v1/pets?includeDeleted=true
```

| 파라미터 | 기본값 | 설명 |
| --- | --- | --- |
| `includeDeleted` | `false` | `true`면 삭제된 프로필도 포함 |
| `limit` | 20 | 최대 100 |
| `offset` | 0 | |

기본은 `status`가 `active`인 것만 돌려줍니다.
`includeDeleted`는 과거 기록의 필터 옵션처럼 **"지금은 없지만 기록에는 남아있는"** 반려동물을
다뤄야 할 때만 씁니다. 앱의 `fetchAllPets()`가 이 용도입니다.

### 응답 `200`

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "몽이",
      "species": "dog",
      "speciesDetail": null,
      "breed": "말티즈",
      "size": "small",
      "weightKg": 4.2,
      "birthDate": "2021-05-03",
      "age": 5,
      "imageUrl": "https://...",
      "healthNotes": null,
      "isPrimary": true,
      "status": "active"
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

`age`는 DB에 없는 계산값입니다. `birthDate`에서 서버가 계산해 함께 내려줍니다.
앱이 나이를 직접 계산하면 기기 시간대에 따라 값이 달라질 수 있어 서버가 담당합니다.
`birthDate`가 `null`이면 `age`도 `null`입니다.

`speciesDetail`은 `species`가 `other`일 때만 값이 있고, 그 외에는 항상 `null`입니다
(DB CHECK 제약 — 문서 상단 참고).

---

## POST /pets

### 요청

```json
{
  "name": "몽이",
  "species": "dog",
  "breed": "말티즈",
  "size": "small",
  "weightKg": 4.2,
  "birthDate": "2021-05-03",
  "imageUrl": "https://...",
  "healthNotes": "슬개골 주의"
}
```

| 필드 | 필수 | 제약 |
| --- | --- | --- |
| `name` | ✅ | 50자 |
| `species` | ✅ | `dog` `cat` `other` |
| `speciesDetail` | 조건부 | `species`가 `other`일 때 필수, 그 외에는 보내면 안 됨. 50자 |
| `size` | — | `small` `medium` `large` |
| `weightKg` | — | 0 이상 |
| `birthDate` | — | 날짜 (`2021-05-03`) |

"기타" 선택 시 요청 예시입니다.

```json
{
  "name": "햄찌",
  "species": "other",
  "speciesDetail": "햄스터"
}
```

첫 번째 반려동물은 서버가 `isPrimary = true`로 설정합니다.

`imageUrl`은 [`uploads.md`](./uploads.md)의 `POST /uploads`로 먼저 받습니다
(`purpose`는 `pet`). `PATCH /pets/{petId}`도 같습니다.

### 응답 `201`

`GET /pets`의 항목 하나와 동일한 구조입니다.

### 에러

| 코드 | 상황 |
| --- | --- |
| 422 | 이름 누락·길이 초과, `weightKg < 0`, `species`가 `other`인데 `speciesDetail` 없음(또는 공백만), `species`가 `other`가 아닌데 `speciesDetail`을 보냄 |

---

## GET /pets/{petId}

### 응답 `200`

`GET /pets`의 항목 하나와 동일한 구조입니다.

### 에러

| 코드 | 상황 |
| --- | --- |
| 403 | 다른 사용자의 반려동물 |
| 404 | 없는 `petId` 또는 삭제됨 |

---

## PATCH /pets/{petId}

보낸 필드만 수정합니다. `imageUrl`을 `null`로 보내면 기본 이미지로 되돌립니다.

### 에러

| 코드 | 상황 |
| --- | --- |
| 403 | 다른 사용자의 반려동물 |
| 404 | 없는 `petId` 또는 이미 삭제됨 |

앱은 이미 삭제된 프로필을 수정하려 할 때를 `PetAlreadyDeletedError`로 구분하고 있는데,
API는 **404로 통일**합니다. 삭제된 리소스는 조회되지 않는다는 공통 규칙(README 6장)에 맞춥니다.

---

## DELETE /pets/{petId}

물리 삭제가 아니라 `pets.deleted_at`을 기록해 `status`를 `deleted`로 바꿉니다.
과거 여행 기록이 참조하는 `petId`가 사라지면 기록이 깨지기 때문입니다.

### 응답 `204`

본문 없음.

### 에러

| 코드 | 상황 |
| --- | --- |
| 403 | 다른 사용자의 반려동물 |
| 404 | 없는 `petId` 또는 이미 삭제됨 |

삭제한 반려동물이 `isPrimary`였다면 남은 반려동물 중 하나를 서버가 대표로 승격합니다.
`pets` 테이블에 사용자당 활성 대표 1건 UNIQUE 제약이 걸려 있어 둘 이상이 될 수 없습니다.

남은 반려동물이 없으면 대표 없이 둡니다. 제약이
`is_primary = true AND deleted_at IS NULL` 조건부라 빈 상태는 허용됩니다.

---

## 변경 이력

| 날짜 | 내용 |
| --- | --- |
| 2026-08-12 | 초안 작성 |
| 2026-08-12 | 확정 규약 반영 — camelCase 응답, `status` 표현, 종류 3종, 목록 래핑. "기타" 종류 DB 컬럼 부재를 확인 필요로 기록 |
| 2026-08-12 | `profileImageUrl`·반려동물 `imageUrl` 업로드 경로를 [`uploads.md`](./uploads.md) 참조로 명시 |
| 2026-08-15 | PR #29 머지 반영 — "기타" 종류 컬럼 부재 해소. `pets.species_detail` 추가로 확인 필요 항목을 걷고, 필드명을 `speciesOther` → `speciesDetail`로 통일. CHECK 제약에 맞춰 422 조건 보완 |
| 2026-08-15 | 탈퇴 후 같은 이메일 재가입을 **차단**으로 확정. 남은 확인 필요는 탈퇴 행 보관 기간뿐 |
| 2026-08-18 | 탈퇴 계정 보관 **30일** 확정(이후 이메일·닉네임 익명화). `preferredTags`를 **영문 코드**로 확정하고 매핑표 추가. 태그 목록 자체는 추천 방식 확정 시 재검토로 보류 |
