# 프론트 타입 · DB 모델 불일치 점검

작성일: 2026-08-12 · 갱신: 2026-08-18 · 대상: `apps/mobile/src` 타입 14개 파일 ↔ `apps/api/app/db/models` 30개 테이블

---

## 요약

API 명세서를 쓰려고 프론트 타입과 DB 모델을 전부 대조했습니다. 결론부터 적습니다.

- **DB와의 불일치보다 앱 내부 불일치가 먼저입니다.** 같은 이름의 타입이 두 곳에 서로 다른 구조로 정의되어 있고, 같은 개념을 한쪽은 한글, 다른 쪽은 영문으로 씁니다.
- **앱 안에 이미 올바른 사례가 3곳 있습니다.** 규칙을 몰라서가 아니라 규칙을 정해두지 않아서 생긴 문제입니다.
- 지금 고치면 타입 rename 수준이지만, API를 붙인 뒤에는 화면 동작까지 함께 깨집니다.

아직 `apiClient`를 실제로 호출하는 코드는 한 줄도 없습니다. **API 연동 전인 지금이 고치기 가장 싼 시점입니다.**

---

## 1. 앱 내부 충돌 — 가장 시급

DB를 논하기 전에 앱 안에서 이미 어긋난 것들입니다.

### 1-1. `Trip` 이 두 곳에 다른 구조로 존재

| 파일 | 식별자 | 구조 |
| --- | --- | --- |
| `src/types/travelLog.ts` | `tripId` | 여행 기록 묶음 (`logCount`, `previewLogs`, `companions`) |
| `src/features/trips/types/trip.ts` | `id` | 여행 일정 (`schedules`, `nights`, `days`, `transport`, `pets`) |

이름이 같고 구조가 완전히 다릅니다. 식별자 필드명도 다릅니다.
import 경로만 바뀌어도 조용히 다른 타입이 들어오므로 위험합니다.

### 1-2. 반려동물 종류가 두 곳에 다르게 정의됨

```ts
// src/types/pet.ts          — 프로필 화면
export type PetSpecies = '강아지' | '고양이';

// src/features/auth/types/auth.ts — 회원가입 화면
export type PetType = 'dog' | 'cat' | 'rabbit' | 'bird' | 'other';
```

회원가입에서 토끼를 고른 사용자가 프로필 화면에 가면 타입에 없는 값이 됩니다.
회원가입 쪽이 DB `pet_species`와 정확히 일치하므로, **프로필 쪽이 잘못된 것**입니다.

### 1-3. 이동수단이 두 타입으로 쪼개짐

```ts
export type TransportType = 'car' | 'walk' | 'ferry';                          // 일정 사이 이동
export type TripTransport = 'rentalCar' | 'publicTransport' | 'ownCar' | 'walk'; // 여행 전체
```

DB에는 `transport_type` 하나뿐이고 7종입니다. 앱은 이를 둘로 나눈 뒤 각각 값을 줄였습니다.

### 1-4. 같은 이름의 `PlaceCategory` 가 두 곳에 다른 타입으로 존재

| 파일 | 타입 |
| --- | --- |
| `features/places/types/place.ts` | `{ id, label, icon }` 객체 |
| `features/trips/types/trip.ts` | `'attraction' \| 'restaurant' \| ...` 문자열 |

---

## 2. 이미 잘 되어 있는 곳 — 이걸 기준으로 삼으면 됩니다

새 규칙을 만들 필요가 없습니다. 앱 안에 정답이 이미 있습니다.

| 파일 | 내용 | DB와 |
| --- | --- | --- |
| `features/auth/constants/signupOptions.ts` | `{ value: 'dog', label: '강아지', icon: '🐶' }` | **완전 일치** |
| `features/auth/types/auth.ts` | `PetType` 5종, `PetSize` 3종 | **완전 일치** |
| `src/types/logDraft.ts` | `WritingStyle` `MomentMood` `GenerationStatus` | **완전 일치** |

핵심은 `signupOptions.ts` 방식입니다.

```ts
{ value: 'dog', label: '강아지' }
   ↑ 데이터·통신용     ↑ 화면 표시용
```

값과 표시 문구를 분리했기 때문에, 나중에 문구를 '반려견'으로 바꿔도 데이터는 그대로입니다.
다국어 대응도 label만 바꾸면 됩니다.

---

## 3. DB와의 불일치 — 유형별

> **아래 대응표는 확정이 아니라 확인 요청입니다.**
> 근거의 강도가 세 가지로 나뉩니다.
>
> | 강도 | 근거 | 예 |
> | --- | --- | --- |
> | 확실 | 프론트 주석에 대응 테이블이 적혀 있음 | `petService.ts:18` "(pets 테이블)", `travelLog.ts:32` "DB의 travel_log_pets" |
> | 확실 | 값·타입이 DB와 완전 일치 | `auth.ts`의 `PetType`, `logDraft.ts`의 `WritingStyle` |
> | **추정** | **구조와 의미가 대응해 보여 문서 작성자가 판단** | **나머지 대부분** |
>
> 세 번째는 각 화면 담당자의 확인이 필요합니다. 이름만 비슷하고 실제로는 다른 값일 수 있습니다.
> 실제로 `logCount`(여행 하나의 기록 수)와 `travelLogsCount`(내 전체 기록 수)는
> 이름이 비슷하지만 집계 범위가 다른 별개 값이었습니다.

### 유형 A. 같은 것을 다른 단어로 부름 → rename으로 해결

| 프론트 | DB | 위치 |
| --- | --- | --- |
| `userId` | `users.id` | `types/user.ts` |
| `petId` | `pets.id` | `types/pet.ts` |
| `logId` | `travel_logs.id` | `types/travelLog.ts` |
| `profileImage` | `users.profile_image_url` / `pets.image_url` | 여러 곳 |
| `weight` | `pets.weight_kg` | `types/pet.ts` |
| `placeName` | `travel_logs.place_name_snapshot` | `types/travelLog.ts` |
| `images` | `inquiries.image_urls` | `types/inquiry.ts` |
| `text` | `chat_messages.content` | `chatbot/types/chatbot.ts` |
| `Trip` | `routes` | `trips/types/trip.ts` |
| `Schedule` | `route_days` | `trips/types/trip.ts` |
| `ScheduleItem` | `route_items` | `trips/types/trip.ts` |
| `TripMemo.scheduleId` | `route_memos.route_day_id` | `trips/types/trip.ts` |
| `companions` | `travel_log_pets` | `types/travelLog.ts` |
| `description` | `notifications.content` | `components/layout/notificationPreview.mock.ts` |

`travelLog.ts` 주석에 `DB의 trip_pets` 라고 적혀 있으나 **그런 테이블은 없습니다.**
실제로는 `route_request_pets` 입니다.

### 유형 B. 값의 표기가 다름 → 변환 규칙 필요

| 프론트 값 | DB 값 | 위치 |
| --- | --- | --- |
| `'강아지'` `'고양이'` | `dog` `cat` | `types/pet.ts` |
| `'실내'` `'야외'` | `indoor` `outdoor` `mixed` | `places/types/place.ts` |
| `'동반 가능'` `'확인 필요'` | `pet_policy_type` 5종 | `route-recommendation/types.ts` |
| `'outdoorOnly'` `'indoorAllowed'` | `outdoor_only` `indoor_allowed` | `trips/types/trip.ts` |
| `'rentalCar'` `'publicTransport'` | `rental_car` `public_transport` | `trips/types/trip.ts` |
| `'partlyCloudy'` | `partly_cloudy` | `trips/types/trip.ts` |

같은 파일 안에서도 규칙이 섞여 있습니다. `logDraft.ts`는 `dog_diary`처럼 snake_case를 그대로 쓰는데
`trip.ts`는 camelCase로 바꿔 씁니다.

### 유형 C. 값의 개수가 다름 → 정보 손실

| 개념 | 프론트 | DB | 빠진 값 |
| --- | --- | --- | --- |
| 반려동물 종류 (프로필) | 2 | 5 | `rabbit` `bird` `other` |
| 이동수단 (일정) | 3 | 7 | `rental_car` `own_car` `taxi` `public_transport` |
| 이동수단 (여행) | 4 | 7 | `taxi` `ferry` `airplane` |
| 날씨 | 5 | 6 | `windy` |
| 반려동물 정책 | 4 | 5 | `unknown` |
| 장소 실내외 | 2 | 3 | `mixed` |
| 일정 항목 분류 | `etc` | `custom` | 이름만 다름 |
| 채팅 역할 | 2 | 3 | `system` |

`unknown`이 빠진 건 특히 문제입니다. 반려동물 정책은 출처가 불확실한 장소가 많아
DB가 기본값을 `unknown`으로 두고 있는데, 앱에는 이를 표시할 방법이 없습니다.

> **2026-08-18 확정 — `unknown`은 회색 "정보 없음" 뱃지로 표시합니다.**
> **앱 반영 완료 (PR #37).** [`PetPolicyBadge.tsx`](../../apps/mobile/src/components/domain/PetPolicyBadge.tsx)의 `BADGE_COLORS`와
> `PetPolicy` 타입을 5종으로 맞췄습니다. [`places.md`](./places.md) 참고.

### 유형 D. 타입·의미가 다름 → rename으로 해결 안 됨

| 프론트 | DB | 문제 |
| --- | --- | --- |
| `age: number` | `pets.birth_date: Date` | 나이는 생년월일에서 계산해야 나옴 |
| `status: 'active'\|'deleted'` | `pets.deleted_at` | 표현 방식이 다름 |
| `ChatMessage.id: number` | `chat_messages.id: UUID` | **숫자 vs 문자열. 런타임 오류 발생** |
| `petFriendly: boolean` | `place_pet_policies.policy_type` 5종 | 5종을 참/거짓으로 뭉갬. **2026-08-18 확정 — 5종 유지, 앱이 `petPolicy`로 통일** |
| `isReservable: boolean` | `places.reservation_required` | **의미가 반대일 수 있음** |
| `Notice.createdAt: 'YYYY.MM.DD'` | `notices.published_at: DateTime` | 표시용 포맷을 데이터로 저장 |
| `Inquiry.createdAt: 'YYYY-MM-DD'` | `inquiries.created_at: DateTime` | 시각 정보 손실 |
| `weather: string` `temperature: string` | enum + `Numeric` | 문자열로 뭉갬 |

`isReservable`과 `reservation_required`는 이름만 보면 뜻이 정반대입니다.
다만 이 필드는 타입 정의와 목업에만 있고 **화면에서 쓰인 적이 없어** 의미가 확정된 적이 없습니다.
지금 DB 쪽 뜻("예약 필수")으로 맞추면 화면 수정 없이 정리됩니다.

### 유형 E. 한쪽에만 있는 필드

**DB에 있는데 앱에 없음**

```text
pets            size, health_notes, is_primary
users           auth_provider, 알림 설정 2개
places          amenities, average_stay_minutes, business_hours
notices         is_pinned, is_active
chat_messages   conversation_id, referenced_place_ids
travel_logs     writing_style, mood, generation_status
```

`travel_logs`의 세 필드는 `logDraft.ts`에는 정의되어 있으나 `TravelLog` 타입에는 없습니다.
생성 후 상태를 화면에서 읽을 수 없습니다.

**앱에 있는데 DB에 없음 (계산해서 내려줘야 하는 값)**

```text
distanceKm, nights, days, logCount, reviewCount, savedCount,
rating, distanceSummary, accommodationSummary, travelStyle
```

이건 불일치가 아닙니다. DB 설계 문서에 "중복 저장하지 않고 조회 시 계산" 으로 명시된 값들이라,
**API 응답에는 반드시 포함되어야 합니다.**

**앱에 있는데 DB에도 없고 계산도 안 되는 값**

```text
notificationPreview.tone     'primary' | 'sea'   아이콘 배경 톤
WeatherSummary.greeting      "좋은 아침이에요"
WeatherSummary.tip           "산책하기 좋은 날씨예요"
```

셋 다 **표현(presentation) 영역**이라 DB에 둘 성격이 아닙니다.

**2026-08-18 확정 — 셋 다 앱이 만듭니다.** API 응답에 포함하지 않고 DB 컬럼도 추가하지 않습니다.
문구와 색상을 바꿀 때 서버 배포가 필요 없습니다.

| 값 | 앱이 만드는 방법 |
| --- | --- |
| `tone` | 목록 인덱스의 짝수/홀수로 번갈아 ([`notifications.md`](./notifications.md)) |
| `greeting` | 날씨와 무관. 시간대를 보거나 고정 문구 ([`weather.md`](./weather.md)) |
| `tip` | 응답의 `condition`·`windSpeed`를 보고 선택 |

---

## 4. 제안

### 4-1. 값 표기 규칙 하나로 통일

`signupOptions.ts` 방식을 앱 전체 규칙으로 정합니다.

```text
데이터·통신     DB와 동일한 영문 snake_case 값 그대로   'rental_car'
화면 표시       별도 label 맵에서 조회                  '렌터카'
```

- 한글을 값으로 쓰는 타입(`PetSpecies`, `environment`, `petStatus`)을 영문 코드로 교체
- camelCase로 변형한 값(`outdoorOnly`, `rentalCar`, `partlyCloudy`)을 DB 값 그대로 복원
- 종류 개수는 DB에 맞춰 복원 (`unknown`, `mixed`, `windy`, `system` 추가)

값은 DB와 맞추되 **필드명 표기법**(`imageUrl` vs `image_url`)은 별도 안건입니다. 4-3 참고.

### 4-2. 앱 내부 충돌 먼저 정리

1. `Trip` 두 개 중 하나를 `TravelLogGroup` 등으로 개명
2. `types/pet.ts`의 `PetSpecies`를 삭제하고 `auth.ts`의 `PetType`으로 통합
3. `TransportType` / `TripTransport`를 DB `transport_type` 하나로 통합
4. `PlaceCategory` 중복 해소

### 4-3. 필드명은 단어를 맞추고 표기법은 각자 관용대로

```text
DB              image_url
프론트           imageUrl        단어는 동일, 표기법만 JS 관용
프론트 (현재)     profileImage    단어가 다름 ← 이게 문제
```

`profileImage → imageUrl`, `petId → id` 처럼 **단어를 맞추는 것**이 목적이고,
snake_case를 그대로 쓰자는 뜻이 아닙니다.

TypeScript라서 일괄 rename 후 `npm run typecheck`가 통과하면 누락이 없다는 게 보장됩니다.
런타임에 조용히 깨지는 종류의 작업이 아닙니다.

참고 규모: `petId` 93곳, `status` 44곳, `weight` 33곳, `profileImage` 28곳.

---

## 5. 결정이 필요한 것

### 담당자가 정하고 공유하면 되는 것

- 값 표기 규칙 (4-1) — DB가 이미 기준이라 사실상 확인 절차
- 이동수단 매핑 — 다만 앱에 **렌터카 선택지가 없습니다.** 제주 여행에서 `rental_car`와 `own_car`
  구분은 중요한데 앱은 `'자가용'` 하나뿐이라 칩 추가가 필요합니다
- `age` 계산 위치 — 서버가 `birthDate`와 `age`를 함께 내리는 쪽을 제안
- `ChatMessage.id` 를 문자열로 수정 — 명백한 버그

### 모여서 정할 것

| 안건 | 이유 |
| --- | --- |
| 필드명 표기 규칙 확정 (4-3) | 프론트 200곳 가까이 영향 |
| 여행 취향 태그 **목록** | 추천 알고리즘 입력값. 장소 데이터에 태그를 다시 붙여야 해서 되돌리기 비쌈 |
| ~~`petFriendly` 를 5종 정책으로 확장할지~~ | **2026-08-18 확정 — 5종 사용.** [`places.md`](./places.md) 참고 |
| ~~탈퇴 후 재가입 허용~~ | **2026-08-15 확정 — 차단.** [`auth.md`](./auth.md) 참고 |

**이미지 업로드 방식은 2026-08-12에 정해졌습니다.** 공통 엔드포인트 `POST /uploads`로 분리하고
서버가 파일을 받아 URL을 돌려주는 방식입니다. [`uploads.md`](./uploads.md) 참고.
**스토리지는 2026-08-18에 AWS S3로 확정**됐습니다(계정은 아직 미생성).

여행 취향 태그 현황 **(2026-08-18 갱신)**

```text
앱 취향   자연, 실내, 카페, 산책, 사진, 조용한, 활동적
장소 태그  바다, 카페, 산책, 포토스팟, 체험, 휴식, 실내관광
```

**표기는 영문 코드로 확정**됐습니다. 앱 취향은 `nature` `indoor` `cafe` `walk` `photo`
`quiet` `active`가 됩니다([`users.md`](./users.md)).

**다만 두 목록을 하나로 합칠지는 여전히 미정입니다.** 둘은 역할이 다른 별개 목록이라
(앱 취향은 사용자 입력, 장소 태그는 서버가 자동 부여) 단어가 달라도 되는 경우가 있습니다.
**추천 방식이 규칙 기반이면 통일이 필수**이고, AI 기반이면 필요 없습니다.
추천 방식이 정해질 때 다시 봐야 합니다.

---

## 6. 다음 단계 제안

**명세서를 쓰기 위해 필요한 것은 규칙 합의뿐입니다.** 프론트 수정이 끝나기를 기다릴 필요가 없습니다.

```
1. 회의        규칙 합의 (4-1, 4-3 방향)
                  ↓
2. 병렬 진행    API 명세서 작성  ┃  프론트 내부 충돌 정리 (4-2)
                  ↓
3. 프론트       명세서 보고 rename 실행
                  ↓
4. 구현        API 개발 후 연동
```

규칙만 정해지면 DB에 있는 필드는 이름이 자동으로 결정됩니다.
명세서에서 새로 작명해야 하는 것은 **DB에 없는 계산·파생 값**뿐입니다.

```text
nights, days, logCount, reviewCount, savedCount,
distanceKm, age, accommodationSummary, travelStyle
```

프론트 rename은 API를 실제로 붙이기 전까지만 끝나면 되므로, 명세서 작성과 동시에 진행할 수 있습니다.
오히려 명세서가 먼저 나오는 편이 낫습니다 — rename의 목표 이름이 명세서에 적혀 있기 때문입니다.

---

## 부록: 확인한 파일

**프론트 타입 (15)**

```text
src/types/          user.ts  pet.ts  profile.ts  travelLog.ts
                    logDraft.ts  inquiry.ts  notice.ts  notification.ts
src/features/       auth/types/auth.ts        auth/constants/signupOptions.ts
                    places/types/place.ts     trips/types/trip.ts
                    chatbot/types/chatbot.ts  home/types/home.ts
                    route-recommendation/types.ts
src/components/     layout/notificationPreview.mock.ts        (PR #26으로 추가)
```

**PR #32·#36 이후 새로 생긴 타입 (대조 안 함)**

```text
src/types/          place.ts                       PetPolicy 정본. trips/types/trip.ts 가 재export
src/features/       places/types/placeDetail.ts    장소 상세 어댑터가 쓰는 단일 모델
                    saved/types/saved.ts           저장한 장소·코스
                    notifications/types/notification.ts
```

> **이 문서는 시점 스냅샷입니다.** 프론트가 머지될 때마다 대조 결과가 달라질 수 있습니다.
> 2026-08-12 PR #26 머지 시점까지 반영했으며, 그때 위 12개 타입 파일은 변경되지 않았고
> `notificationPreview.mock.ts` 하나가 추가되었습니다.
>
> **2026-08-18 — PR #30이 파일을 대거 이동시켰습니다.** `features/*/data/` → `features/*/constants/`,
> `~Mocks.ts` → `~.mock.ts`. 위 경로는 새 위치로 고쳤지만 **타입 내용은 다시 대조하지 않았습니다.**
> `features/places/constants/placeCategories.ts`처럼 새로 생긴 파일도 있어, 다음 점검 때
> 전체를 다시 훑어야 합니다.
>
> **2026-08-18 — PR #32·#36으로 타입 4개가 새로 생겼습니다.** 위 목록에 적어두었고
> 아직 DB와 대조하지 않았습니다. 특히 `places/types/placeDetail.ts`는
> `GET /places/{placeId}` 응답과 직접 맞물리므로 다음 점검에서 우선 볼 대상입니다.

**DB 모델 (30개 테이블 / 12개 Enum)**

```text
apps/api/app/db/models/  users.py  places.py  routes.py  community.py  enums.py
```

---

## 변경 이력

| 날짜 | 내용 |
| --- | --- |
| 2026-08-12 | 최초 점검 |
| 2026-08-12 | PR #26 머지 반영 — `notificationPreview.mock.ts` 대조 추가, 표현 영역 값(`tone` 등) 분류 신설 |
| 2026-08-15 | PR #29 머지 반영 — `places`에서 drop된 `activity_level` `crowd_level` `weather_sensitivity`를 유형 E 목록에서 제거 |
| 2026-08-18 | (율무) PR #37 반영 — `unknown` 뱃지 앱 적용 완료 표시, `PetPolicyBadge` 경로를 `src/components/domain/` 으로 수정, PR #32·#36 신규 타입 4개를 부록에 추가. 분석·판단 내용은 건드리지 않음 |
| 2026-08-18 | 도메인 미정 19건 확정 반영 — `petFriendly` 5종 유지, `unknown` 뱃지 처리, 표현 영역 값(`tone`·`greeting`·`tip`) 셋 다 앱이 생성, 스토리지 S3, 취향 태그 영문 코드. PR #30 파일 이동으로 깨진 `signupOptions.ts` 경로 수정 |
