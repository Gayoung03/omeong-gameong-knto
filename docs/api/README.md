# 오멍가멍 API 공통 규약

작성일: 2026-08-12 · 상태: **초안 (팀 합의 전)**

이 문서는 API를 구현하기 전에 프론트엔드와 백엔드가 미리 합의할 공통 규칙을 정리한 것입니다.
아직 확정된 규격이 아니며, **[제안]** 으로 표시한 항목은 팀 논의로 결정해야 합니다.

| 표기 | 뜻 |
| --- | --- |
| **[확정]** | 이미 코드에 있는 값. 논의 대상 아님 |
| **[제안]** | 코드에 근거가 없어 이 문서에서 제안하는 값. **합의 필요** |

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

## 3. 인증 **[제안]**

`users` 테이블에 `auth_provider`, `provider_user_id`, `password_hash`가 있으므로
자체 로그인과 소셜 로그인을 함께 지원하는 구조입니다.

```text
auth_provider: local | kakao | apple | google
```

### 제안하는 방식

로그인에 성공하면 서버가 자체 토큰을 발급하고, 이후 요청은 헤더에 담아 보냅니다.

```text
Authorization: Bearer <access_token>
```

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

### 결정 필요

- access token만 쓸지, refresh token을 분리할지
- 토큰 만료 시간
- 모바일에서 토큰을 어디에 저장할지 (`expo-secure-store` 등)
- 탈퇴(`users.deleted_at`) 후 같은 계정으로 재가입을 허용할지

---

## 4. 에러 응답 **[제안]**

FastAPI 기본 형식은 다음과 같습니다.

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

### 제안

기본 형식을 그대로 씁니다. 프론트에서 화면에 문구를 직접 매칭해야 하는 경우가 생기면
그때 `code` 필드를 추가하는 쪽으로 확장합니다. 처음부터 감싸면 FastAPI가 자동으로 만들어 주는
검증 에러까지 직접 변환해야 해서 손이 많이 갑니다.

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
| 422 | 요청 형식·타입 검증 실패 (FastAPI 자동) |
| 500 | 서버 오류 |

### 결정 필요

- 기본 형식 유지 여부
- 에러 메시지를 한국어로 내려서 앱이 그대로 표시할지, 코드만 내리고 앱이 문구를 가질지

---

## 5. 목록 조회와 페이지네이션 **[제안]**

장소·리뷰·알림·여행기록 등 목록을 돌려주는 API에 공통으로 적용합니다.

### 제안: limit / offset

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
| 여행기록 | `recorded_date` 최신순 |

### 결정 필요

- limit/offset 채택 여부
- 응답을 `items`로 감쌀지, 배열을 그대로 내리고 개수는 헤더로 줄지

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

### 필드 이름 **[확정]**

DB 컬럼과 같은 snake_case를 씁니다. 앱에서 camelCase로 바꾸는 것은 클라이언트 쪽 책임입니다.

### 삭제 **[제안]**

`users`와 `pets`는 물리 삭제가 아니라 `deleted_at`을 기록하는 soft delete입니다
([DB 문서](../database/README.md) 참고).

API에서는 이렇게 다룹니다.

```text
DELETE 요청              deleted_at 기록
목록 · 상세 조회         deleted_at IS NULL 만 반환
삭제된 리소스 재조회     404
```

앱에는 "삭제됨" 상태를 노출하지 않습니다. 과거 여행 기록에 남은 이름·사진은
`travel_log_pets`의 스냅샷을 쓰므로 삭제 후에도 기록 화면이 유지됩니다.

### 계산해서 내려주는 값 **[확정]**

DB에 저장하지 않고 조회 시 계산하는 값들이 있습니다. **저장하지 않을 뿐 API 응답에는 포함되어야 합니다.**

```text
nights, days      여행 일수 · 숙박 일수
log_count         여행기록 개수
saved_count       저장(즐겨찾기) 개수
review_count      리뷰 개수
여행 총거리 · 총시간
장소까지의 거리
```

### 좌표 **[확정]**

GPS 좌표는 서버 DB에 저장하지 않습니다. 주변 장소 조회처럼 좌표를 받아야 하는 요청은
쿼리 파라미터로 받아 계산에만 쓰고, 로그에 남길 때 마스킹합니다.

```text
GET /api/v1/places?latitude=33.4996&longitude=126.5312&radius=3000
```

---

## 7. Enum 값 **[확정]**

`apps/api/app/db/models/enums.py`에 정의된 12개입니다. 앱과 서버가 같은 문자열을 씁니다.

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

---

## 8. 팀에서 결정할 항목

회의에서 이 목록을 순서대로 확인하면 됩니다.

**인증**

- [ ] access token만 쓸지, refresh token을 분리할지
- [ ] 토큰 만료 시간
- [ ] 모바일 토큰 저장 위치
- [ ] 소셜 토큰을 자체 토큰으로 교환하는 방식이 맞는지
- [ ] 탈퇴 후 재가입 허용 여부

**에러**

- [ ] FastAPI 기본 형식(`detail`)을 그대로 쓸지
- [ ] 에러 메시지를 한국어로 내릴지, 코드만 내릴지

**목록**

- [ ] limit/offset 채택 여부
- [ ] 응답을 `items`로 감쌀지

**기타**

- [ ] soft delete 리소스의 DELETE 응답 코드 (204 통일 여부)
- [ ] 이미지 업로드 방식 — 앱이 직접 스토리지에 올리고 URL만 보낼지, 서버가 받을지
      (`review_images.image_url`, `travel_logs.original_image_url`, `inquiries.image_urls`가 모두 URL 문자열)

---

## 9. 앞으로 작성할 도메인 문서

이 문서의 규약이 확정된 뒤에 도메인별로 나눠 작성합니다.

| 문서 | 대응 DB 테이블 | 엔드포인트 스텁 |
| --- | --- | --- |
| `auth.md` | `users` | `auth.py` |
| `users.md` | `users`, `pets`, `user_travel_preferences` | `users.py`, `pets.py` |
| `places.md` | `places`, `place_business_hours`, `place_pet_policies`, `place_tags`, `place_tag_links`, `favorites` | `places.py` |
| `reviews.md` | `reviews`, `review_images` | `reviews.py` |
| `routes.md` | `route_requests`, `route_request_pets`, `route_request_stays`, `routes`, `route_days`, `route_items`, `route_moves`, `route_checklist_items`, `route_memos` | `routes.py` |
| `travel-logs.md` | `travel_logs`, `travel_log_pets` | `trips.py` |
| `chatbot.md` | `chat_conversations`, `chat_messages` | `chatbot.py` |
| `weather.md` | `weather_snapshots` | `weather.py` |
| `notifications.md` | `notices`, `notifications`, `inquiries` | 없음 |
| `guides.md` | 없음 | `guides.py` |

### 이름이 어긋난 곳

작성 전에 정리가 필요합니다.

- `trips.py` — 파일명은 trips이지만 대응 테이블은 `travel_logs`입니다. 파일명을 바꿀지 정해야 합니다.
- `guides.py` — 대응하는 테이블이 없습니다. 어떤 기능인지 먼저 정의해야 합니다.
- `notices` / `notifications` / `inquiries` — 테이블은 있는데 엔드포인트 스텁 파일이 없습니다.

---

## 변경 이력

| 날짜 | 내용 |
| --- | --- |
| 2026-08-12 | 초안 작성. 인증·에러·페이지네이션은 제안 상태 |
