# 사용자 · 반려동물 API

작성일: 2026-08-12 · 갱신: 2026-08-12 · 상태: **확정 규약 반영** (2026-08-12 팀 회의)

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

## 확인 필요 — DB 컬럼 추가

**"기타" 종류를 선택했을 때 사용자가 입력한 텍스트를 저장할 컬럼이 `pets` 테이블에 없습니다.**

회의에서 반려동물 종류를 강아지 / 고양이 / **기타(사용자 직접 입력)** 로 정했는데,
현재 `pets` 테이블에는 그 입력값을 담을 곳이 없습니다.

```text
현재 pets 컬럼
id, user_id, name, species, breed, size, weight_kg,
birth_date, image_url, health_notes, is_primary,
deleted_at, created_at, updated_at
```

`species`는 enum(`dog` `cat` `rabbit` `bird` `other`)이라 자유 텍스트를 담을 수 없고,
`breed`는 **품종**(말티즈·푸들)을 담는 컬럼이라 종류와 용도가 다릅니다.
품종에 "햄스터"를 넣으면 나중에 품종 기반 기능을 만들 때 데이터가 섞입니다.

모델(`apps/api/app/db/models/users.py`)과 마이그레이션(`5eead3cb186c`) 양쪽을 확인했습니다.

**이 문서에서는 컬럼을 임의로 추가하지 않았습니다.** 아래 요청·응답 예시에는
`speciesOther` 필드를 표시해 두었으나, DB 컬럼과 마이그레이션이 추가되기 전까지는 동작하지 않습니다.

`rabbit` `bird`는 enum에 남아 있지만 앱 선택지에서 제공하지 않습니다.
기존 데이터가 없으므로 enum 자체를 줄이는 선택지도 있습니다 — 이것도 별도 논의가 필요합니다.

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

> **[확인 필요]** 탈퇴 계정 식별값을 얼마나 보관할지, 같은 이메일 재가입을 차단할지.
> 앱은 차단 목록을 갖지 않고 서버가 판단합니다. 보관 기간은 개인정보 처리방침과 함께 정해야 합니다.

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
  "preferredTags": ["바다", "카페", "산책"],
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
  "preferredTags": ["포토스팟", "휴식"]
}
```

| 필드 | 타입 | 제약 |
| --- | --- | --- |
| `defaultPace` | enum | `relaxed` `normal` `packed` |
| `defaultTransport` | enum | `rental_car` `own_car` `taxi` `public_transport` `walk` `ferry` `airplane` |
| `preferredDurationDays` | int | 1 이상 |
| `companionCount` | int | 1 이상 |
| `preferredTags` | string[] | `place_tags.code` 목록 |

### 에러

| 코드 | 상황 |
| --- | --- |
| 422 | `companionCount < 1`, `preferredDurationDays < 1` |

> **[확인 필요]** `preferredTags`에 쓸 태그 목록.
> 앱의 취향 선택지(`자연` `실내` `카페` `산책` `사진` `조용한` `활동적`)와
> DB 설계 문서의 태그(`바다` `카페` `산책` `포토스팟` `체험` `휴식` `실내관광`)가 다릅니다.

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
      "speciesOther": null,
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

`speciesOther`는 `species`가 `other`일 때만 값이 있습니다.
**단, 저장할 DB 컬럼이 아직 없습니다** — 문서 상단 확인 필요 항목 참고.

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
| `speciesOther` | 조건부 | `species`가 `other`일 때 필수 |
| `size` | — | `small` `medium` `large` |
| `weightKg` | — | 0 이상 |
| `birthDate` | — | 날짜 (`2021-05-03`) |

"기타" 선택 시 요청 예시입니다.

```json
{
  "name": "햄찌",
  "species": "other",
  "speciesOther": "햄스터"
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
| 422 | 이름 누락·길이 초과, `weightKg < 0`, `species`가 `other`인데 `speciesOther` 없음 |

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
