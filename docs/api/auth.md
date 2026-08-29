# 인증 API

작성일: 2026-08-12 · 갱신: 2026-08-29 · 상태: **소셜 절 개정안 — 팀 리뷰 필요** (그 외 절은 확정)

> **2026-08-29 소셜 절 전면 개정 (제안)** — 근거는 [변경 이력](#변경-이력) 참고. 요약:
> ① 애플 제외(Android·웹만 출시), ② SDK 토큰 전달 방식 → **서버 콜백 방식**으로 교체
> (웹·앱이 한 흐름 공유, 시크릿이 서버에만 존재, Expo Go 유지),
> ③ 이메일이 겹치면 자동 연동이 아니라 **비밀번호 확인 후 연동** (GitHub #129).

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
| GET | `/auth/{provider}/authorize` | 소셜 로그인 시작 (제공처로 리다이렉트) | — |
| GET | `/auth/{provider}/callback` | 제공처 리다이렉트 수신 (앱이 직접 호출하지 않음) | — |
| POST | `/auth/social/exchange` | 콜백이 준 일회용 코드를 우리 토큰으로 교환 | — |
| POST | `/auth/social/complete` | 이메일 겹침 시 연동 확정 또는 별도 계정 생성 | — |
| POST | `/auth/refresh` | access token 재발급 | — |
| POST | `/auth/logout` | 로그아웃 | 필요 |
| GET | `/auth/check-email` | 이메일 중복 확인 | — |

`{provider}`는 `kakao` `google` 두 값입니다. **애플은 지원하지 않습니다** —
iOS 미출시 결정(2026-08-28)에 따라 제외했습니다.

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

**만료 시간 [확정]** (2026-08-15)

| 토큰 | 만료 | 이유 |
| --- | --- | --- |
| access token | 30분 (`expiresIn: 1800`) | 유출되더라도 유효 시간이 짧음 |
| refresh token | 14일 | 시연·심사 기간에 재로그인 화면이 뜨지 않도록 넉넉히 잡음 |

**JWT 구현 규약** (2026-08-29 추가 — 구현 전 보안 검토 결과 반영)

| 항목 | 규약 |
| --- | --- |
| 서명 | HS256 고정. 검증 시 `algorithms=["HS256"]` 명시 (알고리즘 혼동 공격 차단) |
| 키 | `SECRET_KEY` 환경변수 — 기본값 없음, 없으면 서버 기동 실패 |
| 클레임 | `sub`(user id 문자열) · `typ`(`access` \| `refresh` — 용도 불일치는 `401`) · `jti` · `iat` · `exp` |
| 검증 여유 | clock skew `leeway` 10초 |
| 탈퇴 계정 | **모든 인증 요청과 `POST /auth/refresh`에서 `deleted_at` 확인** — 탈퇴했으면 토큰이 유효해도 `401` |
| 만료 vs 위조 | 외부 응답은 둘 다 같은 `401` (구분해 주면 위조 시도에 힌트). 내부 로그만 구분 |

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
    "speciesDetail": null,
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
| `password` | string | ✅ | **최소 8자·최대 128자.** 서버에서 argon2 해시 후 `users.password_hash`에 저장 |
| `nickname` | string(50) | ✅ | `users.nickname` |
| `pet` | object | — | 없으면 반려동물 없이 가입 |
| `pet.name` | string(50) | ✅ | `pet`을 보낼 때 필수 |
| `pet.species` | enum | ✅ | `dog` `cat` `other` |
| `pet.speciesDetail` | string(50) | 조건부 | `species`가 `other`일 때 필수, 그 외에는 보내면 안 됨 |
| `pet.size` | enum | — | `small` `medium` `large` |
| `travelPreference` | object | — | 건너뛰기 가능 |
| `travelPreference.companionCount` | int | — | 기본 1. 1 이상 |
| `travelPreference.preferredDurationDays` | int | — | 1 이상 |

값은 영문 코드로 주고받습니다. 화면의 "강아지"는 앱이 라벨 맵으로 변환한 결과이고,
요청에는 `dog`이 담깁니다.

`authProvider`는 서버가 `local`로 설정합니다. 클라이언트가 보내지 않습니다.
가입 시 만든 반려동물은 첫 마리이므로 서버가 `pets.is_primary = true`로 설정합니다.

`pet.species`가 `other`일 때 입력한 종류 텍스트는 `pet.speciesDetail`로 받아
`pets.species_detail`에 저장합니다. DB CHECK 제약이 걸려 있어 조합이 어긋나면 저장되지 않습니다
— 자세한 규칙은 [`users.md`](./users.md) 참고.

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
| 409 | 이미 가입된 이메일 (**탈퇴한 계정의 이메일 포함**) |
| 422 | 이메일 형식 오류, 비밀번호 규칙 미달, 필수 필드 누락 |

**탈퇴한 이메일로 재가입 [확정]** — 허용하지 않습니다. (2026-08-15)

탈퇴한 계정(`deleted_at`이 채워진 행)의 이메일로 다시 가입하면 `409`입니다.
살아 있는 계정과 똑같이 취급합니다.

| 근거 | 내용 |
| --- | --- |
| 보관 부담이 없음 | 탈퇴는 soft delete라([`users.py:56`](../../apps/api/app/db/models/users.py)) 행이 남습니다. 이메일은 재가입 허용 여부와 무관하게 그대로 보관됩니다 |
| 추가 작업이 없음 | `users.email`에 UNIQUE가 걸려 있어([`users.py:42`](../../apps/api/app/db/models/users.py)) 차단이 이미 DB 기본 동작입니다. 허용하려면 부분 유니크 인덱스로 바꾸는 마이그레이션이 필요합니다 |
| 소유 확인이 없음 | 회원가입에 이메일 인증 절차가 없습니다. 재가입까지 열면 남의 탈퇴 이메일로 가입할 수 있습니다 |

참고 — 재가입을 열더라도 이전 계정의 데이터가 딸려올 일은 없습니다.
`pets` `routes` `reviews` 등 모든 자식 테이블이 `users.id`(UUID)로만 연결돼 있고
이메일로 묶인 곳이 없어, 재가입은 새 UUID를 받습니다. 이건 이 결정과 무관하게 성립합니다.

**나중에 열고 싶다면** — 탈퇴 후 일정 기간이 지난 행의 이메일을
익명값(`deleted+<uuid>@invalid`)으로 치환하는 배치를 돌리면
UNIQUE 제약을 건드리지 않고 자리를 비울 수 있습니다. 지금 범위에는 넣지 않습니다.

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

## 소셜 로그인 (카카오·구글) — 서버 콜백 방식

**가입과 로그인을 구분하지 않습니다.** 소셜 계정 식별은 신설 예정인
`user_social_accounts` 테이블의 `(provider, provider_user_id)` UNIQUE 로 합니다.
`users`는 `auth_provider` 컬럼이 하나라 "이메일 계정 + 카카오 연동" 같은 다중 수단을
표현할 수 없어 연결 테이블이 필요합니다 — 컬럼 안은 아래와 같고, **실제 추가는
DB 규약대로 `docs/database/README.md` 논의 → 모델+Alembic+DBML 동시 갱신 절차를 따릅니다.**

| 컬럼 | 타입 | 제약 |
| --- | --- | --- |
| `id` | UUID | PK |
| `user_id` | UUID | FK → `users.id` ON DELETE CASCADE |
| `provider` | `auth_provider` enum | `local` 금지 (CHECK) |
| `provider_user_id` | varchar(255) | `UNIQUE(provider, provider_user_id)` |
| `linked_at` | timestamptz | NOT NULL, 기본 now() |

`users.auth_provider`·`provider_user_id`는 **"최초 가입 수단" 기록으로 의미를 고정**하고
로그인 판정에는 쓰지 않습니다 — 연동된 계정은 두 수단을 모두 가지기 때문입니다.

### 왜 SDK 토큰 전달이 아니라 서버 콜백인가 (2026-08-29)

| 이유 | 설명 |
| --- | --- |
| 웹·앱 한 흐름 | 웹 출시가 확정되어 브라우저 리다이렉트 흐름이 어차피 필수. 앱도 같은 흐름을 시스템 브라우저로 타면 구현이 한 벌 |
| Expo Go 유지 | 네이티브 SDK 없이 동작 — 프론트 개발 환경 그대로. 구글 클라이언트 ID도 web 1개로 충분 |
| 시크릿 위치 | 인가 코드 교환이 서버에서 일어나 `client_secret`·REST 키가 앱 번들에 들어가지 않음 |
| 검증 일원화 | 제공처 토큰을 서버만 만지므로 aud/앱 ID 검증 누락 여지가 없음 |

### 흐름

```text
앱/웹: GET /auth/kakao/authorize?returnUrl=<복귀주소> 를 시스템 브라우저로 연다
  → 서버: state 발급(CSRF 방지) 후 제공처 로그인 페이지로 302
  → 사용자: 카카오톡 간편로그인 / 구글 계정 선택
  → 제공처 → GET /auth/kakao/callback?code=...&state=...
  → 서버: state 검증 → 인가 코드를 제공처 토큰으로 교환 → 사용자 정보 조회
       → 일회용 교환 코드(60초, 1회) 발급 → returnUrl 로 302 (?code=<교환코드>)
  → 앱/웹: POST /auth/social/exchange { code }
       → 우리 access/refresh 토큰 수령 (또는 linkRequired — 아래)
```

- `returnUrl`은 **서버 허용 목록**과 대조합니다 — 개발: `exp://*`(Expo Go), 배포 앱: 앱 스킴, 웹: 등록된 오리진. 목록 밖이면 `422`.
- 교환 코드를 쓰는 이유: 우리 토큰을 리다이렉트 URL에 직접 실으면 브라우저 히스토리·로그에 남습니다.
- 서버 검증 의무: **구글은 id_token의 `aud`가 우리 클라이언트 ID인지**, **카카오는 `GET /v1/user/access_token_info`의 앱 ID가 우리 앱인지** 확인합니다. 실패는 `401`, 제공처 무응답은 `502`.

### POST /auth/social/exchange

```json
{ "code": "일회용 교환 코드" }
```

**응답 `200` — 기본 (로그인 완료)**: [토큰 규약](#토큰-규약) 공통 응답 + `isNewUser` + `user`.
`isNewUser: true`면 앱이 반려동물·여행 취향 입력 화면으로 보냅니다
(입력값은 `POST /pets`, `PUT /users/me/travel-preference`로 저장).

**응답 `200` — 이메일이 기존 이메일 계정과 겹칠 때 (로그인 미완료)**:

```json
{
  "linkRequired": true,
  "linkToken": "eyJhbGciOi...",
  "maskedEmail": "tra*****@example.com"
}
```

| 조건 | 결과 |
| --- | --- |
| 제공처가 **검증한** 이메일 = 살아 있는 local 계정 이메일 | `linkRequired` — 즉시 연동하지 않고 비밀번호 확인을 요구 |
| 이메일이 탈퇴 계정과 일치 | 연동 제안 없음 — 새 계정 생성 (`email` 은 비워둠). 탈퇴 계정 부활 금지 |
| 이메일 미제공·미검증 (카카오 `is_email_verified` 확인) | 새 계정 생성 (`email = null`) |
| `(provider, provider_user_id)`가 탈퇴 계정 소유 | `401` — 탈퇴 이메일 재가입 차단과 같은 규칙 |

`linkToken`은 5분짜리 일회용 JWT(`typ: link`)입니다. **자동 연동을 하지 않는 이유**:
local 가입에 이메일 소유 확인이 없어서, 공격자가 남의 이메일로 먼저 가입해두면
피해자의 소셜 로그인이 공격자 계정에 붙습니다. 비밀번호 확인이 소유 증명을 대신합니다 (#129).

### POST /auth/social/complete

`linkRequired`를 받은 앱이 사용자의 선택을 전달합니다.

```json
{ "linkToken": "...", "action": "link", "password": "********" }
```

| `action` | 동작 | 성공 응답 |
| --- | --- | --- |
| `link` | 비밀번호 검증 → 기존 계정에 소셜 연동 추가 | 토큰 공통 응답 + `user` (`isNewUser: false`) |
| `separate` | 연동하지 않고 별도 계정 생성 (`email = null`) | 토큰 공통 응답 + `user` (`isNewUser: true`) |

### 에러 (소셜 공통)

| 코드 | 상황 |
| --- | --- |
| 401 | 제공처 토큰 무효 · 교환/링크 코드 만료·재사용 · `action: link` 비밀번호 불일치 · 탈퇴 계정의 소셜 재로그인 |
| 422 | `returnUrl` 허용 목록 밖 · `provider` 값 오류 · `state` 불일치 |
| 502 | 제공처 서버 응답 없음 |

응답의 `user.email`은 `null`일 수 있습니다 (`users.email` nullable).
`user.authProvider`는 최초 가입 수단입니다. 연동된 수단 목록(`linkedProviders`)은
마이페이지 연동 관리 화면과 함께 **데모 후** 추가합니다 — 그때까지 응답 계약 불변.

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

**refresh token 회전 [확정]** — 회전하지 않습니다. (2026-08-15)

재발급해도 refresh token은 그대로입니다. 응답의 `refreshToken`은 **보낸 것과 같은 값**이고,
앱은 저장 로직을 나눌 필요 없이 매번 덮어쓰면 됩니다.

회전 방식(매번 새 refresh token 발급 + 이전 것 폐기)은 더 안전하지만,
여러 요청이 동시에 만료돼 재발급이 겹치면 먼저 도착한 쪽이 폐기한 토큰을
뒤쪽이 쓰게 되어 멀쩡한 사용자가 로그아웃됩니다. 그 경쟁 처리까지 지금 범위에 넣지 않습니다.

---

## POST /auth/logout

### 요청

본문 없음. 헤더에 access token만 담습니다.

### 응답 `204`

본문 없음. 앱은 저장된 두 토큰을 모두 삭제합니다.

**서버 무효화 [확정]** — 하지 않습니다. (2026-08-15)

이 엔드포인트는 **앱이 토큰을 지웠다는 신호를 받는 것으로 끝납니다.**
서버는 성공 응답만 돌려주고 아무것도 저장하지 않습니다.

즉 로그아웃 직전에 발급된 토큰은 남은 시간 동안 여전히 유효합니다.
무효화하려면 블랙리스트 테이블과 **모든 인증 요청마다 조회**가 붙는데,
지금 범위에 비해 비용이 큽니다. access token 만료가 30분이라 노출 창도 짧습니다.

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

**유지 [확정]** (2026-08-15)

이 엔드포인트는 어떤 이메일이 가입돼 있는지 외부에서 확인할 수 있게 합니다.
그래도 유지합니다 — 회원가입 화면이 입력 즉시 중복을 알려주는 흐름을 전제로 만들어져 있고,
빼면 사용자가 3단계를 다 채운 뒤 마지막에 `409`로 되돌아오게 됩니다.

탈퇴한 계정의 이메일은 `available: false`입니다. 재가입을 막기로 했으므로
살아 있는 계정과 똑같이 "사용 중"으로 답합니다.
여기가 어긋나면 "사용 가능하다더니 가입은 안 되는" 화면이 나옵니다.

---

## 변경 이력

| 날짜 | 내용 |
| --- | --- |
| 2026-08-12 | 초안 작성 |
| 2026-08-12 | 확정 규약 반영 — camelCase 응답, refresh token 분리, `POST /auth/refresh` 추가, 반려동물 종류 3종 |
| 2026-08-15 | PR #29 머지 반영 — 회원가입 요청의 `pet`에 `speciesDetail` 추가, 필드 표에 반영. "저장할 컬럼이 없다"는 확인 필요 항목은 `pets.species_detail` 추가로 해소 |
| 2026-08-15 | 남은 `[확인 필요]` 5건 확정 — 토큰 만료(30분/14일), 탈퇴 이메일 재가입 차단, refresh 회전 없음, 로그아웃 서버 무효화 없음, `check-email` 유지 |
| 2026-08-29 | 비밀번호 규칙 확정 — **최소 8자·최대 128자**, 해시는 argon2 (구현 Phase 3, #137) |
| 2026-08-29 | **소셜 절 전면 개정 (팀 리뷰 대기 — GitHub #129)** — ① 애플 제외(Android·웹만 출시), ② `POST /auth/social`(SDK 토큰 전달) → 서버 콜백 방식(`authorize`/`callback`/`exchange`/`complete`)으로 교체, ③ 이메일 겹침 시 비밀번호 확인 후 연동(자동 연동은 구현 전 보안 검토로 기각 — local 가입에 이메일 소유 확인이 없어 계정 탈취 경로가 됨), ④ 탈퇴 계정은 연동·소셜 재로그인 모두 차단, ⑤ JWT 구현 규약 표 추가(HS256·typ·deleted_at 확인), ⑥ `user_social_accounts` 테이블 안(컬럼 표 포함 — 실제 추가는 DB 규약 절차로). 근거: 웹 출시 확정(08-28), 보안·설계 리뷰(08-28) |
