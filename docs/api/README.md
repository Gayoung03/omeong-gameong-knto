# 오멍가멍 API 공통 규약

작성일: 2026-08-12 · 갱신: 2026-08-18 · 상태: **확정 (2026-08-12 팀 회의) + 도메인 미정 정리 (2026-08-18)**

이 문서는 프론트엔드와 백엔드가 공유하는 API 공통 규칙입니다.
2026-08-12 팀 회의에서 10개 항목을 확정했으며, 아래 표기를 씁니다.

| 표기 | 뜻 |
| --- | --- |
| **[확정]** | 코드에 이미 있거나 팀 회의에서 결정됨 |
| **[확인 필요]** | 결정은 됐으나 구현 전 확인이 남은 항목 |

### 2026-08-12 팀 회의 결정 사항

| # | 항목 | 결정 | 본문 |
| --- | --- | --- | --- |
| 1 | 값 표기 | 영문 코드로 통일 (`dog`). 앱이 화면용 한글 라벨로 변환 | 7장 |
| 2 | 필드명 표기법 | API 응답은 camelCase (`imageUrl`) | 6장 |
| 3 | 반려동물 종류 | 강아지 / 고양이 / 기타(직접 입력) | 7장 |
| 4 | 반려동물 나이 | 서버가 `birthDate`로 계산해 `age` 포함 | 6장 |
| 5 | Soft delete 표현 | `deletedAt` 대신 `status: active \| deleted` | 6장 |
| 6 | `ChatMessage.id` | number가 아닌 UUID 문자열 (버그 수정) | 6장 |
| 7 | 인증 토큰 | access token + refresh token 분리 | 3장 |
| 8 | 에러 응답 | FastAPI 기본 형식(`detail`) 유지 | 4장 |
| 9 | 목록 조회 | limit/offset, `{ items, total, limit, offset }` | 5장 |
| 10 | 이름 통일 기준 | 단어는 DB를 따르고 표기법만 레이어별 관습 | 6장 |

DB 설계 결정은 [`docs/database/README.md`](../database/README.md)가 원본입니다. 이 문서에서 다시 정하지 않고 참조만 합니다.

---

## 1. 현재 구현 상태

`apps/api`는 골격만 잡혀 있고 실제 동작하는 엔드포인트는 2개뿐입니다.

| Method | Path | 설명 |
| --- | --- | --- |
| GET | `/` | 루트 확인용 |
| GET | `/api/v1/health` | 헬스체크 |

`app/api/v1/endpoints/` 아래 `auth.py`, `users.py`, `pets.py`, `places.py`, `reviews.py`,
`routes.py`, `trips.py`, `chatbot.py`, `weather.py`, `guides.py`는 모두 docstring만 있는 빈 파일입니다.
`app/schemas/`(Pydantic 스키마)와 `app/api/dependencies.py`(인증 의존성)도 비어 있습니다.

반면 DB 모델과 마이그레이션은 완성되어 있습니다(테이블 30개, Enum 12개).
그래서 이 문서는 **완성된 DB 모델을 근거로 앞으로 만들 API의 계약을 미리 정하는 것**이 목적입니다.

### FastAPI 자동 문서와의 관계

서버를 띄우면 아래 주소에서 자동 생성 문서를 볼 수 있습니다.

```text
http://localhost:8000/docs     Swagger UI
http://localhost:8000/redoc    ReDoc
```

역할을 이렇게 나눕니다.

- **자동 문서** — 구현 후 실제 스펙. 코드가 바뀌면 같이 바뀌므로 항상 정확합니다.
- **이 문서** — 구현 전 설계 합의 기록. 왜 그렇게 정했는지를 남깁니다.

엔드포인트별 요청·응답 필드는 구현 후 자동 문서를 기준으로 삼고, 이 문서에는 중복해서 적지 않습니다.

---

## 2. Base URL과 버전 **[확정]**

```text
/api/v1
```

`app/core/config.py:11`의 `api_v1_prefix`이며 `app/main.py:24`에서 라우터에 적용합니다.
모바일 클라이언트도 이미 같은 주소를 바라보고 있습니다(`apps/mobile/src/services/apiClient.ts`).

```text
개발 기본값          http://localhost:8000/api/v1
환경변수 덮어쓰기    EXPO_PUBLIC_API_URL
```

`/docs`, `/redoc`, `/`는 prefix 밖에 있습니다.

CORS 허용 출처는 `app/core/config.py:13` 기준입니다.

```text
http://localhost:8081     Expo
http://localhost:19006    Expo Web
```

버전이 올라갈 일이 생기면 `/api/v2`처럼 경로에 넣습니다. 헤더 방식 버저닝은 쓰지 않습니다.

---

## 3. 인증 **[확정]** — 결정: 2026-08-12 팀 회의

`users` 테이블에 `auth_provider`, `provider_user_id`, `password_hash`가 있으므로
자체 로그인과 소셜 로그인을 함께 지원하는 구조입니다.

```text
auth_provider: local | kakao | apple | google
```

### 토큰 구조 — access token + refresh token 분리

로그인에 성공하면 서버가 토큰 두 개를 발급합니다.

```json
{
  "accessToken": "eyJhbGciOi...",
  "refreshToken": "eyJhbGciOi...",
  "tokenType": "bearer",
  "expiresIn": 1800
}
```

| 토큰 | 용도 | 담는 곳 |
| --- | --- | --- |
| access token | 모든 인증 요청에 첨부 | `Authorization` 헤더 |
| refresh token | access token 만료 시 재발급 | `POST /auth/refresh` 요청 본문 |

```text
Authorization: Bearer <accessToken>
```

`expiresIn`은 access token의 남은 초입니다. 앱이 만료 시각을 직접 계산하지 않도록 서버가 내려줍니다.

access token이 만료되면 `401`이 오고, 앱은 refresh token으로 재발급을 시도한 뒤 원래 요청을 다시 보냅니다.
refresh token까지 만료되면 로그인 화면으로 돌려보냅니다.

두 토큰 모두 `expo-secure-store`에 저장합니다. `AsyncStorage`는 암호화되지 않아 쓰지 않습니다.

**만료 시간 [확정]** (2026-08-15) — access token 30분(`expiresIn: 1800`), refresh token 14일.
refresh token은 재발급해도 **회전하지 않습니다**(같은 값을 계속 씁니다).
자세한 내용은 [`auth.md`](./auth.md) 참고.

소셜 로그인도 카카오·애플·구글 토큰을 그대로 쓰지 않고, 서버가 검증한 뒤 자체 토큰으로 교환합니다.
제공처가 4곳이라 각각의 토큰을 앱과 서버가 따로 관리하면 복잡해지기 때문입니다.

```text
소셜 SDK 로그인
    → 서버에 provider token 전달
    → 서버가 제공처에 검증
    → users 조회 또는 생성
    → 자체 access token 발급
```

### 인증이 필요 없는 엔드포인트

```text
헬스체크
회원가입 · 로그인
공지사항 조회
장소 목록 · 상세 조회
```

장소와 공지는 비로그인 상태에서도 앱을 둘러볼 수 있어야 하므로 공개로 둡니다.
단, 즐겨찾기 여부처럼 사용자별 정보는 로그인했을 때만 응답에 포함합니다.

### 인증 관련 확정 (2026-08-15)

| 항목 | 결정 | 근거 |
| --- | --- | --- |
| 토큰 만료 | access 30분 / refresh 14일 | 시연 기간에 재로그인이 뜨지 않도록 |
| refresh 회전 | 하지 않음 | 동시 재발급 경쟁을 처리할 범위가 아님 |
| 로그아웃 시 서버 무효화 | 하지 않음 | 블랙리스트 테이블 + 매 요청 조회 비용이 큼 |
| 탈퇴 후 재가입 | **차단** (`409`) | soft delete라 이메일이 어차피 남고, `users.email` UNIQUE로 이미 막혀 있음 |
| `GET /auth/check-email` | 유지 | 가입 화면이 즉시 중복 안내를 전제로 만들어져 있음. 탈퇴 이메일도 `available: false` |

각 항목의 상세 설명과 구현 주의점은 [`auth.md`](./auth.md)에 있습니다.
**인증은 미정 항목이 남아 있지 않습니다.**

---

## 4. 에러 응답 **[확정]** — 결정: 2026-08-12 팀 회의

**FastAPI 기본 형식을 그대로 씁니다.** 별도 래핑을 하지 않습니다.

```json
{ "detail": "Pet not found" }
```

검증 실패(422)일 때만 형식이 다릅니다.

```json
{
  "detail": [
    { "loc": ["body", "rating"], "msg": "Input should be less than or equal to 5", "type": "less_than_equal" }
  ]
}
```

### 이렇게 정한 이유

처음부터 자체 형식으로 감싸면 FastAPI가 자동으로 만들어 주는 검증 에러(422)까지 직접 변환해야 합니다.
프론트에서 에러 종류를 코드로 구분해야 하는 상황이 실제로 생기면, 그때 `code` 필드를 더하는 쪽으로 확장합니다.

에러 형식이 두 가지(문자열 / 배열)라는 점만 앱이 알고 있으면 됩니다.
`detail`이 배열이면 검증 실패입니다.

### 상태 코드

| 코드 | 쓰는 경우 |
| --- | --- |
| 200 | 조회·수정 성공 |
| 201 | 생성 성공 |
| 204 | 삭제 성공 (응답 본문 없음) |
| 400 | 요청 값은 유효하나 처리할 수 없음 |
| 401 | 토큰 없음·만료·유효하지 않음 |
| 403 | 로그인했으나 권한 없음 (남의 리뷰 수정 등) |
| 404 | 대상이 없음 |
| 409 | 중복 (이미 즐겨찾기한 장소 등) |
| 413 | 업로드 파일 크기 초과 (`POST /uploads` 전용) |
| 415 | 허용하지 않는 파일 형식 (`POST /uploads` 전용) |
| 422 | 요청 형식·타입 검증 실패 (FastAPI 자동) |
| 429 | 같은 장소에 30일 안에 리뷰를 다시 씀 (`POST /places/{placeId}/reviews` 전용) |
| 500 | 서버 오류 |

`413`·`415`·`429`는 각각 한 엔드포인트에서만 쓰입니다
([`uploads.md`](./uploads.md), [`reviews.md`](./reviews.md)).

**챗봇 답변 전송은 이 표를 따르지 않습니다.** `POST /chat/conversations/{id}/messages`만
SSE 스트림이라, 스트림이 시작된 뒤의 실패는 상태 코드가 아니라 `error` 이벤트로 내려갑니다.
[`chatbot.md`](./chatbot.md) 참고.

### 남은 확인 사항

- 에러 메시지를 한국어로 내려서 앱이 그대로 표시할지, 영문으로 내리고 앱이 문구를 가질지

---

## 5. 목록 조회와 페이지네이션 **[확정]** — 결정: 2026-08-12 팀 회의

장소·리뷰·알림·여행기록 등 목록을 돌려주는 API에 공통으로 적용합니다.

### limit / offset

```text
GET /api/v1/places?limit=20&offset=0
```

```json
{
  "items": [],
  "total": 137,
  "limit": 20,
  "offset": 0
}
```

MVP 규모에서는 구현이 단순하고, 전체 개수를 함께 내려줄 수 있어 화면에 "총 137개"를 표시하기 좋습니다.

cursor 방식은 데이터가 계속 추가돼도 페이지가 밀리지 않는 장점이 있지만, 전체 개수를 알 수 없고
정렬 기준이 바뀌면 커서 설계를 다시 해야 합니다. 공모전 범위에서는 과합니다.

### 기본값

```text
limit    기본 20, 최대 100
offset   기본 0
```

### 정렬

목록마다 기본 정렬을 정해 두고, 필요한 곳만 `sort` 파라미터를 추가합니다.

| 목록 | 기본 정렬 |
| --- | --- |
| 장소 | 거리순 (좌표를 받은 경우) / 이름순 |
| 리뷰 | 최신순 |
| 알림 | 최신순 |
| 여행기록 | `recordedDate` 최신순 |

### 목록 응답은 항상 감쌉니다

배열을 그대로 내리지 않습니다. 항목이 하나뿐인 목록도 같은 형태를 유지해,
앱이 목록 응답을 한 가지 방식으로만 다루면 되게 합니다.

```json
{ "items": [], "total": 0, "limit": 20, "offset": 0 }
```

---

## 6. 공통 데이터 규칙

### ID **[확정]**

대부분의 테이블은 UUID를 씁니다.

```text
"id": "550e8400-e29b-41d4-a716-446655440000"
```

`place_tags`, `place_business_hours`만 자동증가 정수입니다.

### 날짜와 시간 **[확정]**

모든 시각 컬럼이 타임존을 포함하므로 ISO 8601로 주고받습니다.

```text
시각   "2026-08-12T14:30:00+09:00"
날짜   "2026-08-12"
시간   "09:30:00"
```

날짜만 있는 필드는 4개뿐입니다.

```text
route_days.route_date
travel_logs.recorded_date
reviews.visited_at
pets.birth_date
```

> **주의** — `visited_at`은 테이블마다 타입이 다릅니다.
> `reviews.visited_at`은 날짜(`2026-08-12`), `travel_logs.visited_at`은 시각(`2026-08-12T14:30:00+09:00`)입니다.
> 앱에서 같은 이름이라고 같은 형식으로 다루면 안 됩니다.

### 필드 이름 **[확정]** — 결정: 2026-08-12 팀 회의

**단어는 DB를 따르고, 표기법만 레이어별 관습을 씁니다.**

```text
DB 컬럼      image_url      snake_case 유지
API 응답     imageUrl       camelCase
앱 타입      imageUrl       그대로 사용
```

단어를 맞춘다는 뜻이지 표기법까지 맞춘다는 뜻이 아닙니다.
`image_url` → `imageUrl` 은 정상이고, `image_url` → `profileImage` 처럼 **단어가 달라지는 것이 금지**입니다.

변환은 서버 Pydantic 응답 스키마에서 합니다. 앱은 받은 그대로 씁니다.

기존 프론트 타입 중 단어가 다른 것들은 DB 단어로 맞춥니다.

| 프론트 현재 | 변경 후 | DB |
| --- | --- | --- |
| `petId` `userId` `logId` | `id` | `pets.id` `users.id` `travel_logs.id` |
| `profileImage` | `imageUrl` / `profileImageUrl` | `pets.image_url` / `users.profile_image_url` |
| `weight` | `weightKg` | `pets.weight_kg` |
| `placeName` (기록) | `placeNameSnapshot` | `travel_logs.place_name_snapshot` |
| `images` (문의) | `imageUrls` | `inquiries.image_urls` |
| `text` (채팅) | `content` | `chat_messages.content` |

전체 목록은 [`type-mismatch-report.md`](./type-mismatch-report.md) 참고.

### 삭제 **[확정]** — 결정: 2026-08-12 팀 회의

`users`와 `pets`는 물리 삭제가 아니라 `deleted_at`을 기록하는 soft delete입니다
([DB 문서](../database/README.md) 참고).

**API 응답에는 `deletedAt` 대신 `status`를 씁니다.**

```json
{ "id": "...", "name": "몽이", "status": "active" }
```

| 값 | 뜻 |
| --- | --- |
| `active` | `deleted_at IS NULL` |
| `deleted` | `deleted_at`이 기록됨 |

시각 자체는 앱에서 쓸 일이 없어 노출하지 않습니다. 앱은 상태만 보고 화면을 그립니다.

```text
DELETE 요청              deleted_at 기록, status가 deleted로 바뀜
목록 · 상세 조회         기본적으로 active만 반환
삭제된 리소스 재조회     404
```

과거 여행 기록에 남은 이름·사진은 `travel_log_pets`의 스냅샷을 쓰므로
삭제 후에도 기록 화면이 유지됩니다.

### 계산해서 내려주는 값 **[확정]**

DB에 저장하지 않고 조회 시 계산하는 값들이 있습니다. **저장하지 않을 뿐 API 응답에는 포함되어야 합니다.**

```text
nights, days      여행 일수 · 숙박 일수
logCount          여행기록 개수
savedCount        저장(즐겨찾기) 개수
reviewCount       리뷰 개수
age               반려동물 나이 — birthDate에서 계산
여행 총거리 · 총시간
장소까지의 거리
```

`age`는 앱이 계산하면 기기 시간대에 따라 값이 달라질 수 있어 서버가 담당합니다.
`birthDate`가 없으면 `age`도 `null`입니다.

### 좌표 **[확정]**

GPS 좌표는 서버 DB에 저장하지 않습니다. 주변 장소 조회처럼 좌표를 받아야 하는 요청은
쿼리 파라미터로 받아 계산에만 쓰고, 로그에 남길 때 마스킹합니다.

```text
GET /api/v1/places?latitude=33.4996&longitude=126.5312&radius=3000
```

---

## 7. Enum 값 **[확정]** — 결정: 2026-08-12 팀 회의

**API는 영문 코드를 그대로 내리고, 화면에 보일 한글은 앱이 라벨로 변환합니다.**

```ts
// 앱이 갖는 라벨 맵 (예시)
const PET_SPECIES_LABEL = { dog: '강아지', cat: '고양이', other: '기타' };
```

값과 표시 문구를 분리하면 화면 문구를 바꿔도 데이터가 그대로입니다.
[`signupOptions.ts`](../../apps/mobile/src/features/auth/constants/signupOptions.ts)의
`petTypeOptions`가 이미 이 방식입니다.

`apps/api/app/db/models/enums.py`에 정의된 12개입니다.

| Enum | 값 |
| --- | --- |
| `auth_provider` | `local` `kakao` `apple` `google` |
| `pet_species` | `dog` `cat` `rabbit` `bird` `other` |
| `pet_size` | `small` `medium` `large` |
| `trip_pace` | `relaxed` `normal` `packed` |
| `transport_type` | `rental_car` `own_car` `taxi` `public_transport` `walk` `ferry` `airplane` |
| `place_environment` | `indoor` `outdoor` `mixed` |
| `pet_policy_type` | `indoor_allowed` `outdoor_only` `partial_allowed` `not_allowed` `unknown` |
| `data_provider` | `tour_api` `kcisa` `visitjeju` `kakao` `tmap` `weather_api` `internal` |
| `route_status` | `generating` `generated` `saved` `ongoing` `completed` `failed` |
| `schedule_item_type` | `attraction` `restaurant` `cafe` `accommodation` `custom` |
| `weather_condition` | `sunny` `partly_cloudy` `cloudy` `rainy` `snowy` `windy` |
| `message_role` | `user` `assistant` `system` |

DB Enum 타입은 아니지만 값이 고정된 문자열 컬럼도 있습니다. 응답 처리 시 함께 맞춰야 합니다.

| 컬럼 | 값 |
| --- | --- |
| `travel_logs.generation_status` | `idle` `uploading` `generating` `completed` `failed` |
| `travel_logs.writing_style` | `dog_diary` `jeju_dialect` |
| `travel_logs.mood` | `happy` `excited` `relaxed` `bittersweet` |
| `inquiries.status` | `pending` `completed` |

`route_status`의 전이 규칙은 [DB 문서](../database/README.md)에 정리되어 있습니다.

```text
generating → generated → saved → ongoing → completed
```

추천을 다시 생성하면 `routes.version`이 올라갑니다.

### 반려동물 종류 **[확정]** — 결정: 2026-08-12 팀 회의

앱에서 제공하는 선택지는 **강아지 / 고양이 / 기타(사용자 직접 입력)** 세 가지입니다.
`pet_species` enum은 그대로 두고 값만 아래처럼 씁니다.

| 앱 선택지 | API 값 | 비고 |
| --- | --- | --- |
| 강아지 | `dog` | |
| 고양이 | `cat` | |
| 기타 | `other` | 사용자가 종류를 직접 입력 |

`rabbit` `bird`는 enum에 남아 있지만 앱 선택지에서는 제공하지 않습니다.

"기타" 선택 시 입력한 텍스트(예: 햄스터)는 `pets.species_detail`에 저장하고,
API에서는 **`speciesDetail`** 로 주고받습니다. 마이그레이션 `8c71f4a2d9e0`에서 추가됐습니다.
`breed`는 품종(말티즈·푸들)을 담는 컬럼이라 종류와 용도가 다릅니다.
상세는 [`users.md`](./users.md) 참고.

### enum이 아닌 약속된 코드 **[확정]** (2026-08-18)

DB가 자유 문자열이나 문자열 배열로 두고 있어 **enum 제약이 없는** 값들입니다.
DB가 막아주지 않으므로 **서버가 아래 값만 넣는다는 약속**으로 관리합니다.
표기 규칙은 위 enum과 같습니다 — 영문 코드를 내리고 앱이 한글 라벨로 바꿉니다.

| 대상 | 컬럼 | 값 |
| --- | --- | --- |
| 여행 취향 태그 | `user_travel_preferences.preferred_tags` (`ARRAY(String)`) | `nature` `indoor` `cafe` `walk` `photo` `quiet` `active` |
| 알림 종류 | `notifications.type` (`String(30)`) | `travel_log_ready` `inquiry_answered` `notice` |
| 문의 카테고리 | `inquiries.category` (`String(50)`) | `account` `pet` `saved` `schedule` `bug` `etc` |

각 목록의 한글 라벨과 근거는 [`users.md`](./users.md), [`notifications.md`](./notifications.md)에 있습니다.

> **여행 취향 태그는 코드 표기만 확정이고 목록 자체는 보류입니다.**
> 위 7개는 현재 앱 화면의 선택지를 코드로 옮긴 것입니다.
> 이 목록을 장소 태그(`place_tags`)와 맞춰야 하는지는 **추천 방식(규칙 기반 / AI)이
> 정해져야** 답이 나옵니다. [`places.md`](./places.md)의 `GET /place-tags` 절 참고.

---

## 8. 결정 현황

### 확정 (2026-08-12 팀 회의)

- [x] 값 표기 — 영문 코드, 앱이 한글 라벨로 변환 (7장)
- [x] 필드명 표기법 — API 응답은 camelCase (6장)
- [x] 반려동물 종류 — 강아지 / 고양이 / 기타(직접 입력) (7장)
- [x] 반려동물 나이 — 서버가 `birthDate`로 계산해 `age` 포함 (6장)
- [x] Soft delete 표현 — `status: active | deleted` (6장)
- [x] `ChatMessage.id` — UUID 문자열 (6장, [`chatbot.md`](./chatbot.md))
- [x] 인증 토큰 — access + refresh 분리 (3장)
- [x] 에러 응답 — FastAPI 기본 형식 유지 (4장)
- [x] 목록 조회 — limit/offset, `{ items, total, limit, offset }` (5장)
- [x] 이름 통일 기준 — 단어는 DB, 표기법은 레이어별 (6장)

### 남은 항목

구현을 막지 않는 것들이라 진행하면서 정합니다.

**2026-08-18 갱신** — 기존 5건 중 2건(스토리지·업로드 / 사용자 등록 장소)이 해소됐고,
도메인 문서 정리 과정에서 3건이 새로 올라왔습니다.

| 항목 | 정해야 할 시점 |
| --- | --- |
| 에러 메시지 언어 (한국어 / 영문 + 앱이 문구 보유) | 첫 도메인 구현 시 |
| 여행 취향 태그 **목록** (코드 표기는 7장에서 확정) | 추천 방식(규칙 기반 / AI) 확정 후 |
| 수동 여행 생성 엔드포인트 (경로·요청 범위·초기 `status`) | 직접 만들기 화면 확정 후 ([`routes.md`](./routes.md)) |
| 여행 가이드 기능 (`guides`) | 화면 기획 후 ([`guides.md`](./guides.md)) |
| 챗봇 RAG 검색 방식 (`app/rag/`가 비어 있음) | 챗봇 구현 시 ([`chatbot.md`](./chatbot.md)) |
| 주인 없는 S3 파일 정리 배치의 주기·유예 시간 | 업로드 구현 후 ([`uploads.md`](./uploads.md)) |

**추천 방식(규칙 기반 / AI)이 아직 정해지지 않았습니다.** 위 표의 태그 목록이 여기 걸려 있고,
`route_requests` 처리 방식도 여기서 갈립니다. 저장소에 `app/rag/{ingestion,prompts,retrieval}`
골격이 잡혀 있어 AI 방식으로 보이지만 확정된 적이 없습니다.

### 추가 확정 (2026-08-12, 팀 회의 외)

회의 이후 명세서를 점검하다 발견한 공백을 메운 항목입니다.
**위 10개와 달리 팀 회의에서 정한 것이 아니므로 공유와 추인이 필요합니다.**

- [x] 이미지 업로드 — 공통 엔드포인트 `POST /uploads`로 분리, 서버가 파일을 받아 URL 반환
      ([`uploads.md`](./uploads.md))

`review_images.image_url`, `travel_logs.original_image_url`, `inquiries.image_urls`,
`users.profile_image_url`, `pets.image_url`, `places.primary_image_url`이 모두 URL 문자열이라
6개 도메인이 이 결정에 공통으로 걸려 있었습니다. 특히 `travel_logs.original_image_url`은
NOT NULL이라 업로드 없이는 여행기록 기능 자체가 성립하지 않습니다.

### 추가 확정 (2026-08-15) — 인증

인증 구현을 바로 시작할 수 있도록 남아 있던 5건을 확정했습니다.
내용은 3장의 표와 [`auth.md`](./auth.md)에 있습니다.

- [x] 토큰 만료 — access 30분 / refresh 14일
- [x] refresh token 회전 — 하지 않음
- [x] 로그아웃 시 서버 무효화 — 하지 않음
- [x] 탈퇴 후 재가입 — 차단 (`409`)
- [x] `GET /auth/check-email` — 유지

**다섯 건 모두 나중에 완화·강화할 수 있는 방향으로 골랐습니다.**
회전과 무효화는 지금 안 넣어도 뒤에 추가할 수 있고,
재가입 차단은 반대로 뒤에 푸는 쪽이 쉽습니다(탈퇴 이메일 익명화 배치).
막아두고 나중에 여는 것은 되지만, 열어두고 나중에 막으면
그 사이에 만들어진 중복 계정을 정리할 방법이 없습니다.

### 추가 확정 (2026-08-18) — 도메인 미정 정리

각 도메인 문서에 `[확인 필요]`로 남아 있던 항목을 훑어 **22건을 확정하고 2건을 보류**했습니다.
`auth.md`를 제외한 모든 도메인이 미정 때문에 구현을 시작하지 못하는 상태였고,
특히 스토리지 미정은 `travel_logs.original_image_url`이 NOT NULL이라
여행기록 기능 자체를 막고 있었습니다.

**위 10개와 달리 팀 회의에서 정한 것이 아니므로 공유와 추인이 필요합니다.**

**업로드** ([`uploads.md`](./uploads.md))

- [x] 스토리지 — **AWS S3** (`ap-northeast-2`). **AWS 계정이 아직 없어 준비 필요**
- [x] 파일 크기 상한 — **10MB**, 용도별로 나누지 않음
- [x] HEIC — **앱이 JPEG로 변환**해 올림. 서버는 HEIC를 받지 않고 `415`
- [x] 삭제 — DB 행은 즉시, S3 파일은 **배치가 지연 삭제** ([`travel-logs.md`](./travel-logs.md))

**장소** ([`places.md`](./places.md))

- [x] 사용자 등록 장소 — **완전 분리**. `GET /places`는 공식 장소만,
      내 장소는 `GET /users/me/places`. **남의 장소는 어떤 경로로도 안 나옴**
- [x] 장소 등록 화면 — **만들기로 확정**. `POST /places` 명세 유지
- [x] `petPolicyType` — 5종 그대로 내리고 `unknown`은 회색 "정보 없음" 뱃지

**사용자** ([`users.md`](./users.md))

- [x] 여행 취향 태그 — **영문 코드**로 저장 (7장 표). 목록 자체는 보류
- [x] 탈퇴 계정 보관 — **30일** 후 이메일·닉네임 익명화

**리뷰** ([`reviews.md`](./reviews.md))

- [x] 탈퇴 사용자 — 리뷰는 **유지**, 작성자만 "탈퇴한 사용자"로 표시
- [x] 재작성 — 같은 장소는 **30일에 한 번** (`429`). 수정은 상시 + `isEdited` 표기

**알림·문의** ([`notifications.md`](./notifications.md))

- [x] 아이콘 톤 — **앱이 순서대로 번갈아** 결정. DB 컬럼 추가 없음
- [x] 알림 종류 — **3종** `travel_log_ready` `inquiry_answered` `notice`
- [x] 이동 경로 — `iconKey`·`actionPath`를 빼고 **`type` + `targetId`만** 내림. 앱이 조립
- [x] 문의 카테고리 — **영문 코드** 6종 (7장 표)

**날씨** ([`weather.md`](./weather.md))

- [x] `greeting`·`tip` — **앱이 생성**. 응답에 포함하지 않음
- [x] 예보 기간 — **3일** (기상청 단기예보만). 중기예보는 쓰지 않음
- [x] 수집 — **1시간 간격**, 지난 예보 **7일 보관**

**챗봇** ([`chatbot.md`](./chatbot.md))

- [x] 답변 — **SSE 스트리밍**(`text/event-stream`). 중단 시 부분 답변 미저장, 중지 버튼은 범위 밖

**여행 추천** ([`routes.md`](./routes.md))

- [x] 폴링 — **2초 간격 / 3분 타임아웃**
- [x] `failureReason` — 컬럼 추가 없이 **응답에만**
- [x] 수동 여행에 재생성 호출 — **`422`**

**보류 2건**

- 수동 여행 생성 엔드포인트 — DB는 준비 완료. **"직접 만들기" 화면 기획 대기**
- 여행 가이드 — **"반려동물과 여행할 때 도움이 되는 정보를 모아 보는 곳"** 으로 성격만 확정.
  화면 기획 대기 ([`guides.md`](./guides.md))

### 앱 코드 수정이 필요한 것

위 결정 중 앱을 함께 고쳐야 하는 항목입니다. 문서에만 반영했고 코드는 아직 그대로입니다.

> `PetPolicyBadge`의 `unknown` 추가는 **2026-08-18 PR #37로 반영 완료**되어 목록에서 뺐습니다.
> 파일도 `src/components/domain/PetPolicyBadge.tsx`로 옮겨졌습니다.

| 파일 | 필요한 수정 |
| --- | --- |
| `features/auth/constants/signupOptions.ts` | `vibeOptions`를 `{ value: 'nature', label: '자연' }` 형태로 |
| `components/layout/NotificationPopup.tsx` | 서버가 `tone`을 안 보내므로 인덱스 기반 계산으로 변경 |
| `features/places/mocks/place.mock.ts` | `petFriendly: boolean` → `petPolicy`로 통일 |
| `types/inquiry.ts` | 문의 카테고리를 코드 + 라벨로 분리 |

---

## 9. 도메인 문서

| 문서 | 대응 DB 테이블 | 엔드포인트 스텁 |
| --- | --- | --- |
| [`auth.md`](./auth.md) | `users` | `auth.py` |
| [`users.md`](./users.md) | `users`, `pets`, `user_travel_preferences` | `users.py`, `pets.py` |
| [`places.md`](./places.md) | `places`, `place_business_hours`, `place_pet_policies`, `place_tags`, `place_tag_links`, `favorites` | `places.py` |
| [`reviews.md`](./reviews.md) | `reviews`, `review_images` | `reviews.py` |
| [`routes.md`](./routes.md) | `route_requests`, `route_request_pets`, `route_request_stays`, `routes`, `route_pets`, `route_days`, `route_items`, `route_moves`, `route_checklist_items`, `route_memos` | `routes.py` |
| [`travel-logs.md`](./travel-logs.md) | `travel_logs`, `travel_log_pets` | `trips.py` |
| [`chatbot.md`](./chatbot.md) | `chat_conversations`, `chat_messages` | `chatbot.py` |
| [`weather.md`](./weather.md) | `weather_snapshots` | `weather.py` |
| [`notifications.md`](./notifications.md) | `notices`, `notifications`, `inquiries` | 없음 |
| [`guides.md`](./guides.md) | 없음 — **보류 (화면 기획 대기)** | `guides.py` |
| [`uploads.md`](./uploads.md) | 없음 (파일은 S3, DB에는 URL만) | 없음 |

`guides.md`만 명세가 없습니다. "반려동물과 여행할 때 도움이 되는 정보를 모아 보는 곳"이라는
성격은 정해졌지만 화면 기획이 없어 DB 테이블부터 설계되지 않은 상태입니다.

### 이름이 어긋난 곳

작성 전에 정리가 필요합니다.

- `trips.py` — 파일명은 trips이지만 대응 테이블은 `travel_logs`입니다. 파일명을 바꿀지 정해야 합니다.
- `guides.py` — 대응하는 테이블이 없습니다. 화면 기획 후 테이블부터 설계해야 합니다.
- `notices` / `notifications` / `inquiries` — 테이블은 있는데 엔드포인트 스텁 파일이 없습니다.
- `uploads.py` — 스텁 파일이 없습니다. 구현 시 새로 만들어야 합니다.

---

## 변경 이력

| 날짜 | 내용 |
| --- | --- |
| 2026-08-12 | 초안 작성. 인증·에러·페이지네이션은 제안 상태 |
| 2026-08-12 | 모바일 기존 타입과 대조. 필드명·enum을 확정에서 제안으로 정정하고 해결 원칙 추가 |
| 2026-08-12 | **팀 회의에서 10개 항목 확정.** 제안 항목을 모두 확정으로 갱신하고 남은 항목만 8장에 정리 |
| 2026-08-12 | 이미지 업로드 엔드포인트 부재를 확인하고 [`uploads.md`](./uploads.md) 신설. 4장에 `413`·`415` 추가, 8장 남은 항목에서 업로드 방식 제거 (팀 회의 외 결정, 추인 필요) |
| 2026-08-12 | 목록에만 있고 본문이 없던 엔드포인트 5개 명세 작성, 사용자 등록 장소 노출 규칙 부재를 8장 남은 항목에 추가 |
| 2026-08-15 | PR #29 머지 반영 — "기타" 종류 컬럼이 `pets.species_detail`로 추가되어 7장 확인 필요를 해소하고 8장에서 제거. 수동 여행 생성 엔드포인트 미정을 8장에 추가 |
| 2026-08-15 | 인증 미정 5건 확정 — 3장에 결정 표 추가, 8장 "남은 항목"에서 토큰 만료·무효화·재가입 제거. [`auth.md`](./auth.md)에 미정 항목이 남아 있지 않음 |
| 2026-08-18 | **도메인 미정 22건 확정 · 2건 보류** — 8장에 결정 절 신설(도메인별 정리 + 앱 수정 필요 목록). 7장에 "enum이 아닌 약속된 코드" 절 추가(취향 태그·알림 종류·문의 카테고리). "남은 항목"에서 스토리지·장소 노출 제거하고 가이드·RAG·파일 정리 배치 추가. 9장 `guides.md` 보류 표시. PR #30 파일 이동으로 깨진 `signupOptions.ts` 링크 수정 |
