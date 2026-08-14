# 오멍가멍 테이블 명세

이 문서는 [`schema.dbml`](./schema.dbml)에 정의된 공모전 MVP 테이블 30개를 설명합니다.

## 공통 규칙

- 기본 PK는 UUID를 사용합니다.
- 코드성 마스터 테이블의 PK는 `bigint` 자동 증가를 사용할 수 있습니다.
- 시각은 PostgreSQL `timestamptz`로 저장하고 API에서 ISO 8601 형식으로 전달합니다.
- 앱은 한국 시간대로 표시하되 DB에서는 UTC 기준 저장을 권장합니다.
- `created_at`, `updated_at`은 서버에서 설정합니다.
- 외부 API 키와 사용자 GPS는 이 업무 DB에 저장하지 않습니다.

## 1. 회원·반려동물

### `users`

앱 회원의 계정과 기본 프로필을 저장합니다.

| 컬럼 | 설명 |
| --- | --- |
| `id` | 회원 PK |
| `email` | 로컬 로그인 이메일. 소셜 로그인은 null 가능 |
| `password_hash` | 비밀번호 해시. 원문 저장 금지 |
| `auth_provider` | `local`, `kakao`, `apple`, `google` |
| `provider_user_id` | 소셜 제공자의 회원 식별자 |
| `nickname` | 앱 표시 닉네임 |
| `profile_image_url` | 프로필 이미지 URL |
| `inquiry_answer_notification_enabled` | 문의 답변 알림 수신 여부 |
| `marketing_notification_enabled` | 마케팅 알림 수신 여부 |
| `deleted_at` | 회원 탈퇴 시각. null이면 활성 회원 |

주요 관계:

- 회원 1명은 반려동물, 루트, 리뷰, 챗봇 대화를 여러 건 가집니다.
- `(auth_provider, provider_user_id)`는 유일해야 합니다.

### `pets`

회원이 등록한 반려동물 프로필입니다.

| 컬럼 | 설명 |
| --- | --- |
| `user_id` | 반려동물의 보호자 |
| `name` | 반려동물 이름 |
| `species` | 강아지, 고양이 등 종류 |
| `species_detail` | `species=other`일 때 사용자가 입력한 실제 종류 |
| `breed` | 품종 자유 문자열. MVP에서 별도 품종 테이블 사용 안 함 |
| `size` | 소형, 중형, 대형 |
| `weight_kg` | 입장 무게 제한 판단에 사용 |
| `birth_date` | 나이 계산용 |
| `health_notes` | 건강 주의사항 |
| `is_primary` | 대표 반려동물 여부 |
| `deleted_at` | 프로필 삭제 시각. null이면 활성 프로필 |

주의사항:

- 회원별 `is_primary = true`는 최대 한 건만 허용합니다.
- `species=other`이면 공백이 아닌 `species_detail`이 필수이고, 다른 종류에서는 null이어야 합니다.
- 추천 요청에서 선택한 반려동물은 `route_request_pets`, 실제 저장된 여행의 동반 반려동물은 `route_pets`를 사용합니다.
- 과거 여행과 기록의 참조를 보존하기 위해 물리 삭제하지 않습니다.

### `user_travel_preferences`

회원의 평소 여행 취향을 저장합니다. 루트 입력 화면의 기본값으로 사용합니다.

| 컬럼 | 설명 |
| --- | --- |
| `user_id` | 회원 PK와 같은 1:1 FK |
| `default_pace` | 기본 여행 속도 |
| `default_transport` | 기본 이동수단 |
| `departure_location` | 자주 사용하는 출발지 문자열 |
| `preferred_duration_days` | 기본 여행 기간 |
| `companion_count` | 기본 동행 인원 |
| `preferred_tags` | 평소 선호 태그 배열 |

이번 여행에서 선택한 조건은 이 테이블을 수정하지 않고 `route_requests`에 저장합니다.

## 2. 장소

### `places`

서비스에서 사용하는 통합 장소 마스터입니다. TourAPI, KCISA, 비짓제주, 카카오의 같은 실제 장소를 여기에 한 번만 저장합니다.

| 컬럼 | 설명 |
| --- | --- |
| `name` | 표준 장소명 |
| `category` | 관광지, 카페, 음식점, 숙박 등 |
| `region` | 애월, 성산, 중문 등 서비스 지역 |
| `address`, `road_address` | 지번·도로명주소 |
| `latitude`, `longitude` | 지도·거리 계산용 좌표 |
| `primary_image_url` | 대표 이미지 |
| `description` | 앱에 표시할 대표 소개 |
| `description_source` | 소개 출처 |
| `environment` | 실내, 실외, 혼합 |
| `amenities` | 주차장, 화장실, Wi-Fi 등 편의시설 배열 |
| `average_stay_minutes` | 추천 일정 체류시간 |
| `created_by_user_id` | 사용자가 직접 등록한 장소일 때 작성 회원 |
| `is_active` | 서비스 노출 여부 |

장소 소개 우선순위:

```text
비짓제주 > TourAPI > KCISA > 확인된 정보로 만든 자동 요약
```

### `place_external_refs`

통합 장소와 외부 데이터 제공자의 ID를 연결합니다.

| 컬럼 | 설명 |
| --- | --- |
| `place_id` | 통합 장소 FK |
| `provider` | TourAPI, KCISA, 비짓제주, 카카오 등 |
| `external_id` | `contentid`, 카카오 `place_id` 등 |
| `source_url` | 외부 상세 페이지 |
| `source_updated_at` | 제공처 자료 수정 시각 |
| `last_synced_at` | 우리 서버 마지막 동기화 시각 |

`(provider, external_id)`는 유일해야 합니다. 외부 제공처별 장소 테이블을 따로 만들지 않습니다.

### `place_business_hours`

장소의 요일별 영업·휴게시간을 저장합니다.

| 컬럼 | 설명 |
| --- | --- |
| `day_of_week` | 0=일요일, 1=월요일, …, 6=토요일 |
| `opens_at`, `closes_at` | 영업 시작·종료 시간 |
| `break_start_at`, `break_end_at` | 휴게시간 |
| `is_closed` | 해당 요일 휴무 여부 |
| `raw_text` | 파싱 전 CSV/API 원문 |

일정 생성 시 방문 예정 시간에 영업 중인 장소만 후보로 사용합니다.

### `place_pet_policies`

장소의 반려동물 동반 조건을 저장합니다.

| 컬럼 | 설명 |
| --- | --- |
| `policy_type` | 실내 허용, 실외만 허용, 부분 허용, 불가, 미확인 |
| `allowed_species` | 허용 동물 종류 배열 |
| `allowed_sizes` | 허용 크기 배열 |
| `max_weight_kg` | 최대 무게 제한 |
| `carrier_required` | 이동장 필수 여부 |
| `leash_required` | 목줄 필수 여부 |
| `vaccination_required` | 예방접종 확인 여부 |
| `extra_fee_amount` | 동반 추가 요금 |
| `notes` | 기타 제한사항 원문 |
| `source`, `verified_at` | 정보 출처와 확인 시각 |
| `reliability_score` | 정보 신뢰점수 0~100 |

카카오에만 있고 동반 정보가 없는 장소는 `unknown`으로 저장합니다.

### `place_tags`

추천에 사용하는 표준 태그 사전입니다.

```text
바다, 카페, 산책, 포토스팟, 체험, 휴식, 실내관광
```

### `place_tag_links`

장소와 추천 태그의 N:M 관계입니다.

| 컬럼 | 설명 |
| --- | --- |
| `place_id`, `tag_id` | 장소·태그 복합 PK |
| `confidence` | AI/규칙 분류 신뢰도 0~1 |
| `source` | 태그 출처 |

비짓제주의 모든 `alltag`를 그대로 넣지 않고 추천에 필요한 표준 태그만 연결합니다.

## 3. 루트 입력

### `route_requests`

루트 추천 버튼을 누른 시점의 최종 입력 조건 스냅샷입니다.

| 컬럼 | 설명 |
| --- | --- |
| `user_id` | 요청 회원 |
| `title` | 여행 이름 |
| `start_at`, `end_at` | 여행 시작·종료 일시 |
| `departure_location` | 사용자가 입력한 출발지 문자열 |
| `departure_place_id` | 출발지가 장소 마스터에 있을 때 FK |
| `pace` | 이번 여행에 적용한 속도 |
| `transport` | 이번 여행 이동수단 |
| `preferred_tags` | 이번 여행 선호 태그 배열 |
| `request_text` | AI에게 전달할 추가 요청 |

사용자 기본 취향을 사용했더라도 최종 적용값을 여기에 저장합니다.

### `route_request_pets`

루트 요청과 동행 반려동물의 N:M 연결 테이블입니다.

반려동물이 여러 마리면 모든 반려동물의 종류·크기·무게 조건을 모두 충족하는 장소만 추천합니다.

### `route_request_stays`

루트 입력 단계에서 선택한 숙소입니다.

| 컬럼 | 설명 |
| --- | --- |
| `route_request_id` | 루트 요청 FK |
| `place_id` | 장소 DB에 있는 숙소 FK |
| `name`, `address` | 사용자가 직접 입력한 숙소도 지원 |
| `check_in_at`, `check_out_at` | 숙박 기간 |

숙소를 직접 입력하면 `place_id` 없이 이름·주소를 저장할 수 있습니다.

## 4. 추천 루트·내 여행

### `routes`

AI 추천 결과와 사용자가 저장한 내 여행의 공통 루트 본체입니다.

| 컬럼 | 설명 |
| --- | --- |
| `route_request_id` | 추천 생성에 사용한 입력 조건. 수동 여행은 null |
| `status` | 생성 중, 추천 완료, 저장, 여행 중, 완료, 실패 |
| `creation_type` | `recommended`(추천 생성) 또는 `manual`(사용자 직접 생성) |
| `version` | AI 재추천 버전 |
| `pace`, `transport` | 적용된 여행 조건 |
| `explanation` | AI 추천 설명 |
| `total_score` | 종합 추천 점수 |
| `pet_safety_score` | 반려동물 안전 점수 |
| `style_keywords` | 내 여행에서 편집 가능한 여행 키워드 배열 |
| `share_token`, `is_public` | 공유 링크 제어 |

상태 흐름:

```text
generating → generated → saved → ongoing → completed
             └→ failed
```

추천 결과를 내 여행에 저장할 때 별도 여행 테이블을 복사하지 않고 `status`를 `saved`로 변경합니다.
사용자가 직접 만든 여행은 `creation_type=manual`, `route_request_id=null`, `status=saved`로 생성합니다.

### `route_pets`

저장된 여행과 실제 동반하는 반려동물의 N:M 연결 테이블입니다. 추천 여행과 수동 여행이 공통으로 사용합니다.

### `route_days`

루트의 일자별 구조입니다.

| 컬럼 | 설명 |
| --- | --- |
| `route_id` | 루트 FK |
| `day_number` | 1일차, 2일차 등 순서 |
| `route_date` | 실제 날짜 |
| `weather_snapshot_id` | 일정 생성에 사용한 날씨 |
| `title` | 일자별 요약 제목 |

`(route_id, day_number)`는 유일합니다.

### `route_items`

하루 일정에 들어간 방문 장소입니다.

| 컬럼 | 설명 |
| --- | --- |
| `route_day_id` | 일자 FK |
| `place_id` | 장소 마스터 FK |
| `custom_place_name` | DB에 없는 사용자 직접 입력 장소 |
| `item_type` | 관광지, 식당, 카페, 숙소 등 |
| `sort_order` | 해당 일자 내 순서 |
| `starts_at`, `ends_at` | 방문 예정 일시 |
| `stay_minutes` | 예상 체류시간 |
| `recommendation_score` | 장소 추천 점수 |
| `recommendation_reason` | 추천 근거 |
| `is_selected` | 사용자 선택 유지 여부 |

`place_id`와 `custom_place_name` 중 하나는 반드시 존재해야 합니다.

### `route_moves`

연속한 일정 항목 사이의 이동 구간입니다.

| 컬럼 | 설명 |
| --- | --- |
| `from_item_id` | 출발 일정 항목 |
| `to_item_id` | 도착 일정 항목 |
| `transport` | 이동수단 |

TMAP의 거리·시간·polyline은 이 테이블에 영구 저장하지 않습니다.

## 5. 날씨·TMAP

### `weather_snapshots`

루트 생성·재조정에 사용한 제주 지역별 날씨 예보 스냅샷입니다.

| 컬럼 | 설명 |
| --- | --- |
| `region` | 예보 지역 |
| `forecast_at` | 예보 대상 시각 |
| `condition` | 맑음, 흐림, 비, 눈, 강풍 등 |
| `temperature` | 대표 기온 |
| `min_temperature`, `max_temperature` | 최저·최고 기온 |
| `precipitation_probability` | 강수확률 0~100 |
| `humidity`, `wind_speed` | 습도·풍속 |
| `source_updated_at` | 기상 데이터 갱신 시각 |

과거 루트가 어떤 날씨를 기준으로 생성됐는지 재현하는 데 사용합니다.

### `route_calculation_cache`

TMAP으로 계산한 두 좌표 사이 경로의 단기 캐시입니다.

| 컬럼 | 설명 |
| --- | --- |
| 출발·도착 좌표 | TMAP 요청 좌표 |
| `transport` | 자동차, 도보 등 |
| `requested_departure_at` | 시간대별 예상 경로 기준 |
| `distance_meters` | 거리 |
| `duration_minutes` | 예상 이동시간 |
| `polyline` | 지도 경로 표시용 |
| `calculated_at`, `expires_at` | 계산·만료 시각 |

TMAP 약관에 맞춰 24시간 이상 사용하지 않고 만료된 값은 재계산합니다.

## 6. 여행 부가기능

### `route_checklist_items`

저장한 여행의 준비물 체크리스트입니다.

| 컬럼 | 설명 |
| --- | --- |
| `route_id` | 저장된 루트 |
| `category` | 반려동물, 여행, 기타 |
| `label` | 준비물 내용 |
| `is_checked` | 준비 완료 여부 |
| `is_recommended` | 앱 추천 항목 여부 |
| `sort_order` | 표시 순서 |

### `route_memos`

여행 전체 또는 특정 일자에 작성한 메모입니다.

| 컬럼 | 설명 |
| --- | --- |
| `route_id` | 루트 FK |
| `route_day_id` | 특정 일자 메모일 때 FK. 전체 메모는 null |
| `title`, `content` | 메모 제목·본문 |

## 7. 즐겨찾기·리뷰

### `favorites`

회원과 즐겨찾기한 장소의 N:M 연결 테이블입니다.

`(user_id, place_id)`를 복합 PK로 사용하여 중복 저장을 막습니다.

### `reviews`

사용자의 장소 방문 리뷰입니다.

| 컬럼 | 설명 |
| --- | --- |
| `user_id`, `place_id` | 작성자·리뷰 장소 |
| `pet_id` | 함께 방문한 반려동물 |
| `rating` | 별점 1~5 |
| `content` | 리뷰 본문 |
| `pet_policy_accurate` | 앱의 동반 정보가 정확했는지 |
| `visited_at` | 실제 방문일 |

`pet_policy_accurate`는 향후 `place_pet_policies.reliability_score`를 갱신하는 근거로 사용할 수 있습니다.

### `review_images`

리뷰의 여러 이미지 URL과 표시 순서를 저장합니다. 실제 이미지 파일은 DB가 아니라 오브젝트 스토리지에 저장합니다.

## 8. 여행 기록

### `travel_logs`

사용자가 사진으로 남기는 여행 순간과 AI 이미지 생성 결과를 저장합니다.

| 컬럼 | 설명 |
| --- | --- |
| `user_id` | 기록 소유자 |
| `route_id` | 연결된 내 여행. 개별 기록은 null 가능 |
| `place_id` | 연결된 장소. 직접 입력한 장소는 null 가능 |
| `place_name_snapshot` | 기록 당시 장소명 |
| `recorded_date`, `visited_at` | 날짜 그룹과 방문 시각 |
| `original_image_url` | 재생성·편집에 사용하는 원본 이미지 |
| `generated_image_url` | 목록·공유에 사용하는 완성 이미지 |
| `writing_style` | 강아지 일기, 제주 방언 등 생성 스타일 |
| `mood` | 행복, 신남, 여유 등 선택한 분위기 |
| `generation_status` | 업로드·생성 진행 상태 |
| `personal_message` | 사용자가 별도로 남긴 한 줄 |
| `is_representative` | 날짜 그룹 대표 기록 여부 |

여행별 로그 개수와 미리보기는 이 테이블에서 집계하며 `routes`에 중복 저장하지 않습니다.

### `travel_log_pets`

여행 기록과 함께한 반려동물의 N:M 연결 및 표시용 스냅샷입니다.

| 컬럼 | 설명 |
| --- | --- |
| `travel_log_id` | 여행 기록 FK |
| `pet_id` | 반려동물 FK. 향후 물리 삭제에 대비해 null 가능 |
| `pet_name_snapshot` | 기록 당시 이름 |
| `pet_profile_image_snapshot` | 기록 당시 프로필 이미지 |

활성 반려동물이 존재하면 현재 프로필을 표시하고, 찾을 수 없을 때 스냅샷을 fallback으로 사용합니다.

## 9. 고객지원

### `inquiries`

회원의 1:1 문의와 운영자 답변을 한 행에 저장합니다.

| 컬럼 | 설명 |
| --- | --- |
| `user_id` | 문의 작성 회원 |
| `category` | 계정, 반려동물, 코스, 일정, 오류, 기타 |
| `status` | `pending` 또는 `completed` |
| `title`, `content` | 문의 제목·본문 |
| `image_urls` | 첨부 이미지 URL 배열 |
| `answer`, `answered_at` | 운영자 답변과 답변 시각 |

MVP에서는 첨부 이미지의 개별 메타데이터가 필요하지 않아 이미지 테이블을 추가하지 않습니다.

### `notices`

서비스 공지사항을 저장합니다.

| 컬럼 | 설명 |
| --- | --- |
| `title`, `content` | 공지 제목·본문 |
| `is_pinned` | 상단 고정 여부 |
| `is_active` | 노출 여부 |
| `published_at` | 게시 시각 |

### `notifications`

종 버튼에서 보여주는 회원별 앱 내부 알림과 읽음 상태를 저장합니다.

| 컬럼 | 설명 |
| --- | --- |
| `user_id` | 알림을 받을 회원 |
| `type` | 문의 답변, 여행 일정, 코스 생성, 정책 변경, 마케팅 등 알림 종류 |
| `title`, `content` | 알림 제목·본문 |
| `icon_key` | 앱에서 표시할 아이콘 식별자 |
| `action_path` | 알림을 눌렀을 때 이동할 Expo Router 내부 경로 |
| `is_read` | 읽음 여부 |
| `created_at`, `read_at` | 생성·읽은 시각 |

알림 수신 여부는 `users`의 설정 컬럼으로 판단하고, 실제 발생한 알림만 이 테이블에 추가합니다.
Expo Push 발송 결과는 저장하지 않으므로 `notification_deliveries` 테이블은 만들지 않습니다.

## 10. AI 챗봇

### `chat_conversations`

사용자와 AI의 대화방입니다.

| 컬럼 | 설명 |
| --- | --- |
| `user_id` | 대화 소유자 |
| `route_id` | 특정 루트를 수정하는 대화일 때 FK |
| `title` | 대화방 제목 |

일반 장소 질문은 `route_id` 없이 생성할 수 있습니다.

### `chat_messages`

대화방의 시간순 메시지입니다.

| 컬럼 | 설명 |
| --- | --- |
| `conversation_id` | 대화방 FK |
| `role` | 사용자, AI, 시스템 |
| `content` | 메시지 본문 |
| `referenced_place_ids` | 답변 지도·장소 카드에 표시할 장소 ID 배열 |
| `model_name` | 응답 생성에 사용한 모델 |

AI가 장소를 자유 문자열로만 반환하지 않고, 실제 `places.id`를 함께 반환하도록 합니다.

## 삭제 규칙 초안

| 부모 | 자식 처리 권장 |
| --- | --- |
| `users` 삭제 | 법적 보존 범위 확정 후 익명화 또는 파기, 알림은 cascade |
| `places` 삭제 | 실제 삭제 대신 `is_active = false` |
| `route_requests` 삭제 | 요청 반려동물·숙소·루트 cascade |
| `routes` 삭제 | day·item·move·checklist·memo cascade |
| `reviews` 삭제 | `review_images` cascade |
| `pets` 삭제 | soft delete. 여행 기록 연결과 스냅샷 유지 |
| `travel_logs` 삭제 | `travel_log_pets` cascade, 이미지 스토리지 파일 별도 삭제 |
| `inquiries` 삭제 | 보존 정책에 따라 첨부 이미지와 함께 삭제 |
| `chat_conversations` 삭제 | `chat_messages` cascade |

Alembic migration에서 FK별 `ON DELETE`를 명시적으로 정의합니다.

## MVP 이후 확장 후보

다음 기능이 실제 범위로 확정될 때만 테이블을 추가합니다.

- 반려동물 성격·품종 마스터
- 장소 소개 이력과 필드별 출처
- 편의시설 마스터
- 사용자 동반 정책 검증
- 푸시 알림 발송 이력
- 문의 이미지 개별 메타데이터
- 운송사별 반려동물 탑승 규정
- 데이터 동기화 이력
- RAG 문서·pgvector 임베딩
