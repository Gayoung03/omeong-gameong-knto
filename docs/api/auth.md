# 인증 API

작성일: 2026-08-12 · 갱신: 2026-08-12 · 상태: **확정 규약 반영** (2026-08-12 팀 회의)

공통 규약은 [`README.md`](./README.md)를 따릅니다. 이 문서에 적용된 확정 사항은 다음과 같습니다.

| # | 확정 내용 | 이 문서에서 |
| --- | --- | --- |
| 2 | 응답 필드는 camelCase | 모든 예시 |
| 7 | access token + refresh token 분리 | 로그인·가입 응답, `POST /auth/refresh` |
| 8 | 에러는 FastAPI 기본 형식(`detail`) | 에러 표 |
| 1·3 | 값은 영문 코드, 종류는 강아지/고양이/기타 | 회원가입 요청 |

관련 DB 테이블: `users`, `pets`, `user_travel_preferences`

---

## 엔드포인트 목록

| Method | Path | 설명 | 인증 |
| --- | --- | --- | --- |
| POST | `/auth/signup` | 이메일 회원가입 | — |
| POST | `/auth/login` | 이메일 로그인 | — |
| POST | `/auth/social` | 소셜 로그인·가입 | — |
| POST | `/auth/refresh` | access token 재발급 | — |
| POST | `/auth/logout` | 로그아웃 | 필요 |
| GET | `/auth/check-email` | 이메일 중복 확인 | — |

회원 탈퇴는 `DELETE /users/me` 입니다. [`users.md`](./users.md) 참고.

---

## 토큰 규약

로그인·회원가입·소셜 로그인 세 곳이 모두 같은 토큰 응답을 돌려줍니다.

```json
{
  "accessToken": "eyJhbGciOi...",
  "refreshToken": "eyJhbGciOi...",
  "tokenType": "bearer",
  "expiresIn": 1800
}
```

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `accessToken` | string | 모든 인증 요청의 `Authorization` 헤더에 담음 |
| `refreshToken` | string | access token 만료 시 재발급용 |
| `tokenType` | string | 항상 `bearer` |
| `expiresIn` | int | access token 남은 초. 앱이 만료 시각을 직접 계산하지 않도록 서버가 제공 |

```text
Authorization: Bearer <accessToken>
```

두 토큰 모두 `expo-secure-store`에 저장합니다.

> **[확인 필요]** 만료 시간은 구현 시점에 정합니다. 위 `1800`은 임시값입니다.

---

## POST /auth/signup

이메일로 가입합니다. 앱의 회원가입은 3단계(계정 → 반려동물 → 여행 취향)이고
[`SignupScreen.tsx`](../../apps/mobile/src/features/auth/screens/SignupScreen.tsx)가 마지막에 한 번에 제출하므로,
**계정·반려동물·여행 취향을 한 요청으로 받습니다.**

`users` + `pets` + `user_travel_preferences` 세 테이블에 한 트랜잭션으로 저장합니다.

### 요청

```json
{
  "email": "traveler@example.com",
  "password": "********",
  "nickname": "여행자",
  "pet": {
    "name": "몽이",
    "species": "dog",
    "size": "small"
  },
  "travelPreference": {
    "preferredDurationDays": 2,
    "defaultTransport": "rental_car",
    "departureLocation": "제주시",
    "preferredTags": ["바다", "카페"],
    "companionCount": 1
  }
}
```

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `email` | string | ✅ | `users.email`. 중복 불가 |
| `password` | string | ✅ | 서버에서 해시 후 `users.password_hash`에 저장 |
| `nickname` | string(50) | ✅ | `users.nickname` |
| `pet` | object | — | 없으면 반려동물 없이 가입 |
| `pet.name` | string(50) | ✅ | `pet`을 보낼 때 필수 |
| `pet.species` | enum | ✅ | `dog` `cat` `other` |
| `pet.size` | enum | — | `small` `medium` `large` |
| `travelPreference` | object | — | 건너뛰기 가능 |
| `travelPreference.companionCount` | int | — | 기본 1. 1 이상 |
| `travelPreference.preferredDurationDays` | int | — | 1 이상 |

값은 영문 코드로 주고받습니다. 화면의 "강아지"는 앱이 라벨 맵으로 변환한 결과이고,
요청에는 `dog`이 담깁니다.

`authProvider`는 서버가 `local`로 설정합니다. 클라이언트가 보내지 않습니다.
가입 시 만든 반려동물은 첫 마리이므로 서버가 `pets.is_primary = true`로 설정합니다.

> **[확인 필요]** `pet.species`가 `other`일 때 사용자가 입력한 종류 텍스트를 받을 필드가 필요하나,
> **`pets` 테이블에 저장할 컬럼이 없습니다.** 자세한 내용은 [`users.md`](./users.md)의 확인 필요 항목 참고.

### 응답 `201`

```json
{
  "accessToken": "eyJhbGciOi...",
  "refreshToken": "eyJhbGciOi...",
  "tokenType": "bearer",
  "expiresIn": 1800,
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "traveler@example.com",
    "nickname": "여행자",
    "profileImageUrl": null,
    "authProvider": "local",
    "status": "active"
  }
}
```

가입 직후 바로 로그인 상태가 되도록 토큰을 함께 내려줍니다.

### 에러

| 코드 | 상황 |
| --- | --- |
| 409 | 이미 가입된 이메일 |
| 422 | 이메일 형식 오류, 비밀번호 규칙 미달, 필수 필드 누락 |

> **[확인 필요]** 탈퇴한 이메일(`status`가 `deleted`인 계정)로 재가입을 허용할지.
> 앱은 차단 목록을 갖지 않고 서버가 판단합니다
> ([`accountService.ts:22`](../../apps/mobile/src/features/auth/services/accountService.ts) 주석).

---

## POST /auth/login

### 요청

```json
{
  "email": "traveler@example.com",
  "password": "********"
}
```

### 응답 `200`

`POST /auth/signup` 과 동일한 구조입니다.

### 에러

| 코드 | 상황 |
| --- | --- |
| 401 | 이메일 또는 비밀번호 불일치 |
| 401 | 탈퇴한 계정 |

이메일이 없는 경우와 비밀번호가 틀린 경우를 **구분하지 않고 같은 401**을 돌려줍니다.
구분해서 알려주면 가입된 이메일 목록을 알아낼 수 있기 때문입니다.

---

## POST /auth/social

카카오·애플·구글 로그인입니다. **가입과 로그인을 구분하지 않습니다.**
`(auth_provider, provider_user_id)` 조합으로 기존 계정을 찾고, 없으면 새로 만듭니다.
`users` 테이블에 이 조합의 UNIQUE 제약이 걸려 있습니다.

```text
앱: 소셜 SDK 로그인
  → 서버에 provider와 providerAccessToken 전달
  → 서버가 제공처 API로 검증하고 사용자 정보 조회
  → users 조회 또는 생성
  → 자체 access token + refresh token 발급
```

제공처 토큰을 앱이 계속 들고 있지 않도록, 서버가 검증 후 자체 토큰으로 교환합니다.

### 요청

```json
{
  "provider": "kakao",
  "providerAccessToken": "..."
}
```

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `provider` | enum | ✅ | `kakao` `apple` `google` (`local` 불가) |
| `providerAccessToken` | string | ✅ | 소셜 SDK가 발급한 토큰 |

### 응답 `200`

```json
{
  "accessToken": "eyJhbGciOi...",
  "refreshToken": "eyJhbGciOi...",
  "tokenType": "bearer",
  "expiresIn": 1800,
  "isNewUser": true,
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": null,
    "nickname": "카카오사용자",
    "profileImageUrl": "https://...",
    "authProvider": "kakao",
    "status": "active"
  }
}
```

`isNewUser`가 `true`면 앱이 반려동물·여행 취향 입력 화면으로 보냅니다.
소셜 가입은 그 정보를 받을 수 없기 때문입니다.

`email`은 `null`일 수 있습니다. 애플 로그인은 이메일 제공을 거부할 수 있고,
`users.email`도 nullable로 설계되어 있습니다.

### 에러

| 코드 | 상황 |
| --- | --- |
| 401 | 제공처 토큰이 유효하지 않음 |
| 502 | 제공처 서버 응답 없음 |

---

## POST /auth/refresh

access token이 만료됐을 때 refresh token으로 새로 발급받습니다.
이 요청에는 `Authorization` 헤더를 담지 않습니다. 만료된 토큰을 보낼 이유가 없기 때문입니다.

### 요청

```json
{ "refreshToken": "eyJhbGciOi..." }
```

### 응답 `200`

```json
{
  "accessToken": "eyJhbGciOi...",
  "refreshToken": "eyJhbGciOi...",
  "tokenType": "bearer",
  "expiresIn": 1800
}
```

`user` 객체는 포함하지 않습니다. 필요하면 `GET /users/me`를 따로 호출합니다.

### 에러

| 코드 | 상황 |
| --- | --- |
| 401 | refresh token 만료·위조·무효화됨 |

401을 받으면 앱은 저장된 토큰을 지우고 로그인 화면으로 보냅니다.

### 앱에서의 흐름

```text
요청 → 401
  → POST /auth/refresh
     성공 → 새 accessToken 저장 → 원래 요청 재시도
     실패 → 토큰 삭제 → 로그인 화면
```

동시에 여러 요청이 401을 받을 수 있으므로, 앱은 재발급 요청이 한 번만 나가도록 묶어야 합니다.

> **[확인 필요]** refresh token을 재발급 때마다 새로 줄지(rotation), 기존 것을 계속 쓸지.
> 위 예시는 새로 주는 방식입니다.

---

## POST /auth/logout

### 요청

본문 없음. 헤더에 access token만 담습니다.

### 응답 `204`

본문 없음. 앱은 저장된 두 토큰을 모두 삭제합니다.

> **[확인 필요]** 서버에서 refresh token을 무효화할지.
> 무효화하려면 저장소(블랙리스트 또는 토큰 테이블)가 필요합니다.
> 하지 않으면 이 엔드포인트는 앱이 토큰을 지우는 것으로 끝납니다.

---

## GET /auth/check-email

회원가입 화면에서 이메일 중복을 미리 확인합니다.

### 요청

```text
GET /api/v1/auth/check-email?email=traveler@example.com
```

### 응답 `200`

```json
{ "available": false }
```

### 에러

| 코드 | 상황 |
| --- | --- |
| 422 | 이메일 형식 오류 |

> **[확인 필요]** 이 엔드포인트는 가입 여부를 외부에 노출합니다.
> 회원가입 UX와 보안 중 어느 쪽을 택할지 정해야 합니다.
> 빼고 제출 시 409로만 알려주는 선택지도 있습니다.

---

## 변경 이력

| 날짜 | 내용 |
| --- | --- |
| 2026-08-12 | 초안 작성 |
| 2026-08-12 | 확정 규약 반영 — camelCase 응답, refresh token 분리, `POST /auth/refresh` 추가, 반려동물 종류 3종 |
