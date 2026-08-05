# 오멍가멍 공모전 MVP 데이터베이스

이 문서는 공모전 시연과 앱 출시 1차 버전에 필요한 데이터만 대상으로 합니다. 장기 확장 기능을 미리 모두 테이블로 만들지 않고, 필요해지면 Alembic migration으로 추가합니다.

## ERD 확인

[`schema.dbml`](./schema.dbml)을 [dbdiagram.io](https://dbdiagram.io)에 붙여 넣으면 ERD를 확인할 수 있습니다.

각 테이블의 용도와 컬럼 설명은 [`table-reference.md`](./table-reference.md)에서 확인할 수 있습니다.

## 전체 규모

```text
테이블 25개
Enum 12개
```

## 도메인별 테이블

| 도메인 | 테이블 |
| --- | --- |
| 회원/반려동물 | `users`, `pets`, `user_travel_preferences` |
| 장소 | `places`, `place_external_refs`, `place_business_hours`, `place_pet_policies`, `place_tags`, `place_tag_links` |
| 루트 입력 | `route_requests`, `route_request_pets`, `route_request_stays` |
| 루트 결과/내 여행 | `routes`, `route_days`, `route_items`, `route_moves` |
| 날씨/이동 | `weather_snapshots`, `route_calculation_cache` |
| 여행 부가기능 | `route_checklist_items`, `route_memos` |
| 저장/리뷰 | `favorites`, `reviews`, `review_images` |
| AI 챗봇 | `chat_conversations`, `chat_messages` |

## 사용자 기본 취향과 이번 여행 조건

### 사용자 기본 취향

`user_travel_preferences`에 회원가입·마이페이지에서 설정한 평소 취향을 저장합니다.

```text
기본 여행 속도: 여유롭게
기본 이동수단: 렌터카
평소 선호: 바다, 카페, 산책
```

### 이번 여행 조건

`route_requests`에 루트 추천 화면에서 입력한 이번 여행 조건을 저장합니다.

```text
이번 여행 속도: 알차게
이번 이동수단: 택시
이번 선호: 실내 관광지, 맛집
```

추천 우선순위:

```text
이번 여행에서 직접 입력한 값
    > 사용자 기본 취향
    > 서비스 기본값
```

추천 당시 최종 적용된 속도, 이동수단과 태그를 `route_requests`에 스냅샷으로 저장합니다. 나중에 사용자의 기본 취향이 바뀐다고 과거 추천 조건이 바뀌지 않습니다.

## 여행 속도

| 속도 | 하루 장소 | 기본 휴식 | 일정 시간대 |
| --- | ---: | ---: | --- |
| `relaxed` | 3개 | 40분 | 10~18시 |
| `normal` | 4개 | 25분 | 09~19시 |
| `packed` | 5개 | 15분 | 08~21시 |

여행 속도는 장소 테이블의 속성이 아니라 추천 서비스의 일정 생성 규칙입니다. 장소의 `average_stay_minutes`, `activity_level`, `crowd_level`, `weather_sensitivity`와 함께 사용합니다.

## 반려동물 프로필

```text
species: enum
size: enum
breed: varchar
```

품종별 검색·의료·입장 규칙을 구현하지 않으므로 `pet_breeds` 테이블은 만들지 않습니다. 반려동물 성격 태그도 MVP 추천에서 제외합니다.

## 장소 데이터 통합

TourAPI, KCISA CSV, 비짓제주, 카카오별로 장소 테이블을 만들지 않습니다. 실제 장소는 `places`에 한 번만 저장하고 제공처 ID를 `place_external_refs`에 연결합니다.

```text
places: 함덕해수욕장

place_external_refs
- TOUR_API  / contentid
- KAKAO     / place_id
- VISITJEJU / contentsid
- KCISA     / source key
```

중복 판별 순서:

1. 외부 ID
2. 전화번호
3. 도로명주소
4. 장소명 유사도 + 50m 이내 좌표
5. 확신이 낮으면 수동 검토

## 제공처별 역할

| 제공처 | 사용 정보 |
| --- | --- |
| TourAPI | 공식 관광지, 이미지, 반려동물 동반 조건 |
| KCISA CSV | 운영시간, 크기, 제한사항, 실내외 정보 |
| 비짓제주 | 제주 장소 소개, 관광 태그, 편의시설 |
| 카카오 | 장소 검색, 주소, 좌표, 전화번호, 상세 URL |
| TMAP | 장소 간 거리, 이동시간, 경로 |

카카오 Local API에서 긴 소개문·반려동물 조건을 가져오지 않습니다. 장소 설명은 다음 우선순위로 `places.description`에 선택 저장합니다.

```text
비짓제주 소개
> TourAPI 소개
> KCISA 기본 설명
> 확인된 구조화 정보로 만든 짧은 문장
```

카카오맵 상세 페이지의 리뷰·이미지를 크롤링해 저장하지 않습니다.

## 태그와 편의시설

추천에 사용하는 핵심 태그만 `place_tags`, `place_tag_links`로 관리합니다.

```text
바다, 카페, 산책, 포토스팟, 체험, 휴식, 실내관광
```

편의시설은 MVP에서 `places.amenities` 배열로 관리합니다.

```text
주차장, 화장실, wifi, 엘리베이터, 편의점
```

## 반려동물 동반 정책

`place_pet_policies` 한 행에 장소의 동반 정책을 저장합니다.

```text
policy_type
allowed_species[]
allowed_sizes[]
max_weight_kg
carrier_required
leash_required
vaccination_required
extra_fee_amount
notes
source
verified_at
reliability_score
```

MVP에서는 허용 동물·크기를 별도 연결 테이블로 쪼개지 않고 PostgreSQL 배열로 저장합니다.

## 추천 결과와 내 여행

추천과 저장된 여행에 동일한 일정 구조가 필요하므로 둘을 별도 테이블로 중복하지 않습니다.

```text
routes.status

generated  AI 추천 완료
saved      사용자가 내 여행에 저장
ongoing    여행 중
completed  여행 종료
```

사용자가 추천안을 저장하면 `routes.status` 값을 `generated`에서 `saved`로 변경합니다. 추천을 다시 생성하면 `version`을 증가시킵니다.

## TMAP 경로 계산

TMAP 전용 장소 테이블은 만들지 않습니다. `places`의 좌표를 전달하고 결과를 `route_calculation_cache`에 최대 24시간만 캐시합니다.

```text
places 좌표
    ↓
TMAP API
    ↓
route_calculation_cache
```

`route_moves`에는 일정 순서와 이동수단만 영구 저장합니다. 거리·시간·polyline은 캐시가 만료되면 TMAP에서 다시 계산합니다.

추천 시 호출량을 줄이는 순서:

1. 반려동물 정책·운영시간·날씨 필터
2. 취향 점수로 상위 후보 선정
3. 직선거리로 근거리 후보 축소
4. 최종 후보에만 TMAP 호출

## GPS와 개인위치정보

공모전 MVP에서는 GPS를 현재 위치 마커와 주변 장소 조회에만 사용합니다.

```text
현재 위치
→ 단말 내부 처리 우선
→ 자체 DB 저장 금지

루트 추천
→ 사용자가 선택한 출발 장소 좌표 사용
→ 실시간 GPS 사용 안 함
```

GPS를 서버로 전송해야 하는 경우 DB에 저장하지 않고 API·프록시·오류 로그에서 좌표를 마스킹합니다. 정식 출시 전 위치기반서비스 신고·약관·동의 절차를 확인합니다.

## PostgreSQL/Alembic 제약조건

- `reviews.rating BETWEEN 1 AND 5`
- `activity_level`, `crowd_level`, `weather_sensitivity BETWEEN 1 AND 5`
- 강수확률·신뢰점수 0~100
- `route_requests.end_at > start_at`
- `route_items.ends_at > starts_at`
- 위도 -90~90, 경도 -180~180
- `pets.is_primary`는 사용자별 최대 1건
- `route_moves.from_item_id <> to_item_id`
- `route_calculation_cache.expires_at > calculated_at`
- 자주 조회하는 FK와 상태·카테고리 index
- 반경 검색 고도화 시 PostGIS `geography(Point, 4326)` + GIST index

## 추후 필요할 때만 추가할 테이블

다음은 MVP에서 제외합니다.

```text
반려동물 성격 태그
품종 코드
장소 소개 이력
편의시설 코드/MA 테이블
사용자 동반 정책 검증
리뷰 도움 투표
여행 로그
알림
운송사 규정
데이터 동기화 이력
RAG 문서/임베딩
```

기능 구현이 확정될 때 Alembic migration으로 추가합니다.
