# 루트 추천 재설계 — 정의·리뷰·스키마 변경안

작성일: 2026-09-07 · 상태: **초안 (팀 공유·추인 대기)** · 작성: viowlet

이 문서는 루트 추천 기능을 다시 정의하고, 그 정의에 필요한 DB 스키마 변경을 제안한다.
API 계약 변경은 추인 후 [`docs/api/routes.md`](../api/routes.md)에, 스키마 변경은
[`docs/database/README.md`](../database/README.md)·`schema.dbml`·`table-reference.md`에 반영한다.
**이 문서가 승인되기 전에는 코드를 바꾸지 않는다.**

---

## 1. 왜 다시 설계하는가

### 1.1 현재 구현이 실제 데이터 위에서 하는 일

설계 문서상 파이프라인은 `하드 필터 → 6축 점수 → 그리디 일정 조립 → TMAP` 이고 코드도 그렇게
짜여 있다. 그러나 2026-09-07 팀 DB 기준으로 실제 동작을 추적하면 다음과 같다.

| 축 | 설계 의도 | 실제 |
| --- | --- | --- |
| 취향 (0.30) | 사용자 태그 ↔ 장소 태그 Jaccard | **항상 0.** `place_tags.code`는 영문(`sea`)인데 `STANDARD_TAGS`는 한글("바다")이라 교집합이 비어 있다. "맛집" 카테고리 예외만 동작 |
| 반려 (0.32) | 반려동물 편의 | 장소 정책만 본다. **반려동물 인자를 받지 않는다** |
| 근접 (0.23) | 숙소·출발지 거리 | 정상 동작 |
| 날씨 (0.15) | 강수확률 × 실내/실외 | 장소 `environment` null 810/1,266 → 대부분 중립 0.5 |
| 평점·인기 (0) | — | 리뷰 0건. 죽은 코드 |

결과적으로 현재 엔진은 **"반려 정책 + 거리"로만 도는 근접 순 나열기**다. 여기에 체류시간이
전 장소 60분(1,265/1,266 null), 관광지 145곳 중 자연 명소(주상절리·성산일출봉·섭지코지·비자림·
사려니숲·만장굴·용머리해안) 부재, 정책 unknown 638곳 통과 허용이 겹친다.

### 1.2 기능의 정의 (대화로 합의, 2026-09-07)

> 루트 추천은 여행을 떠나기 전, 반려동물과 **확실히 함께 갈 수 있는 곳**만으로 며칠간의 하루를
> **실행 가능하게** 짜 주는 기능이다. 개인화의 중심은 사람의 취향이 아니라 반려동물의 크기·나이·
> 컨디션이며, 날씨와 기온에 따라 실내·실외 구성을 바꾼다. 모든 장소에는 동반 조건과 근거 출처가
> 붙고, 슬롯마다 대안 후보가 함께 나와 사용자가 고칠 수 있다. 동선 근처의 동물병원을 안전망으로
> 보여준다. 확인되지 않은 장소는 기본적으로 쓰지 않고, 쓸 때는 확인 필요를 명시한다.
> 취향·인기 축은 유지하되 전면에 두지 않는다.

세부 결정:

| # | 결정 | 비고 |
| --- | --- | --- |
| D1 | 중심 상황은 **떠나기 전 전체 일정 계획** | 숙소 당일·도중 재추천은 같은 엔진의 변형으로 후속 |
| D2 | 개인화 중심을 **반려동물**로. `pets`에 활동량·차멀미·사회성, 요청에 **이번 여행 컨디션** 스냅샷 | README "성격 태그 MVP 제외" 결정을 **개정** (§4.1) |
| D3 | 기본 후보는 **확실히 동반 가능한 곳만**. unknown 정책은 부족할 때만 "확인 필요" 라벨 + 전화번호로 채움 | `places.md`의 `unknown` 뱃지 개념을 루트 항목으로 확장 |
| D4 | **완전 실패 → 부분 성공**. 못 채운 슬롯은 비워 두고 확인 필요 후보를 붙임. 응답에 완성도 포함 | `routes.md` "식당 부족 시 실패" 문장 **개정** (§5) |
| D5 | **슬롯별 대안 후보 2~3개** 저장. 사용자는 슬롯 안에서 교체 (기존 `PUT /route-items/{id}/place` 재사용). 자유 배치는 서버 확장 여지만 | |
| D6 | 날씨·기온은 점수 축이 아니라 **하루 구성 규칙** (비·더위 → 실내 비중 상향, 정오~15시 실외 회피) | 예보 범위(+3일) 밖이면 규칙 미적용 |
| D7 | 동선·숙소 근처 **동물병원**(24시 우선)을 안전망으로 응답에 첨부. 펫 맡김(펫호텔) 추천은 **보류** | 저장 없는 계산값 |
| D8 | 식당은 동반 가능 우선, 부족 시 `outdoor_only` 식당을 "야외 대기 가능" 대안으로. **음식 종류**를 카카오 로컬로 보강 | D3와 같은 tier 메커니즘 |
| D9 | 모든 장소에 동반 조건·근거 출처 문장. 추천 논리는 규칙, **LLM은 여행 전체 설명 1회**만 | 장소별 LLM 호출 안 함 (지연) |
| D10 | 취향·인기 축 유지, 화면 전면에서 제외 | `applied_weights` 6키 유지 (하위호환) |
| D11 | **데이터 보강 포함**: 태그 코드 통일, 카테고리별 체류시간 기본값, 환경 추정, 카테고리 오염 정리, 자연 명소 수동 큐레이션(50~80곳, 정책 출처 URL 기록) + 공공데이터·비짓제주로 좌표·설명 보강 | 관광공사 TourAPI 응답은 **저장 금지 유지**, 실시간만 |

---

## 2. 리뷰 결과와 반영

설계·DB·명세 정합성 세 관점으로 리뷰했다. 반영한 항목만 적는다.

### 2.1 정의끼리의 의존 관계 (설계 리뷰)

- **태그 코드 통일(D11)과 가중치 재조정은 같은 PR.** 태그를 통일하는 순간 죽어 있던 취향 축 0.30이
  부활해 결과가 "사람 취향 30%"로 기울어 D2와 반대가 된다. 통일과 동시에 `INITIAL_WEIGHTS`를
  낮춰 잡는다.
- **D3(확실한 곳만)은 D11(명소 큐레이션) 뒤에 켠다.** 순서를 뒤집으면 D4가 "거의 빈 일정을 정상
  응답으로 내보내는 장치"가 된다.
- **D3·D8·D6·D2는 하나의 완화 사다리로 통합.** 조립기의 기존 3단계 완화(`_best_candidate_with_diversity`)
  에 이동시간 상한 완화 → 환경 선호 완화 → unknown 정책 폴백을 4·5·6단계로 붙인다. 규칙을
  루프 안 `if`로 흩뿌리지 않는다.
- **D9의 9할은 LLM이 아니라 필드 노출.** `place_pet_policies.source`·`source_url`·`verified_at`·
  `caution_note`가 이미 있다. 응답에 내리면 된다.

### 2.2 재설계와 무관하게 지금 위험한 것 (설계 리뷰)

- **TMAP 호출 상한 없음.** 후보가 영업시간에 안 맞아 거절될 때마다 TMAP 호출이 버려지고, 루프에
  호출 횟수 상한이 없다. 시연 중 3분 타임아웃을 넘길 수 있는 실제 버그. 하루당 호출 상한과
  직선거리 폴백을 **재설계 전에 먼저** 넣는다.
- **`taste` 프리셋을 고르면 점수가 낮아진다.** 죽은 취향 축이 2배 부스트되어 정규화 후 0.46을 먹는다.
- **이동시간 추정의 정확도.** 검수 중 실측(TMAP 38구간)으로 확인: 직선÷500m/min 은 짧은 구간의 고정 시간을 놓쳐 평균 오차 34%. 한라산 횡단·산길 도로배율은 1.46~1.73이지만 보수적 속도가 이미 흡수해 별도 배율은 오차를 키움(19.0%). `7분 + 직선÷600m/min` 로 교체(17.1%). 근본 대책은 Phase 3 슬롯 계획의 **권역** 개념(하루 안에서 남북을 오가지 않게).
- **`applied_weights` 하위호환.** `Weights`가 6키 고정·합=1·`extra="forbid"`라 키를 줄이면 기존
  요청 행으로 편집 API가 500이 난다. **키는 유지하고 날씨 값만 0으로 고정**한다 (D10).

### 2.3 계약 충돌 (명세 리뷰)

| 재설계 항목 | 충돌하는 확정 문서 | 처리 |
| --- | --- | --- |
| D4 부분 성공 | `routes.md` "저녁 식당이 부족하면 **실패로 처리**하며 조용히 대체하지 않는다" | 문장 개정. "조용히 대체 금지"의 정신은 **빈 슬롯 + 확인 필요 라벨**로 지킨다 |
| D4 부분 성공 | `route_status` enum 6개, 앱 폴링 종료 조건이 `generated`/`failed` 이분법 | **enum에 값을 추가하지 않는다.** 부분 성공도 `generated`. `failed`는 "모든 날이 비었음"으로 좁힌다. 완성도는 응답 계산값 |
| D2 pets 컬럼 | `database/README.md` 149행 "반려동물 성격 태그도 MVP 추천에서 제외", 352행 추후 목록 | **결정 개정** (§4.1). 성격 태그 테이블이 아니라 추천 규칙에 쓰는 컬럼 3개 |
| D5 대안 저장 | README "테이블 추가는 먼저 논의된 것만" | 이 문서가 그 논의 (§4.3) |
| D8 카카오 | README 190행 "카카오에서 긴 소개문·반려동물 조건을 가져오지 않는다" | 음식 종류는 그 범위 밖. 문장에 "음식 종류(`cuisine`)는 가져온다" 추가 |

**그대로 유지하는 확정 사항**: 폴링 2초/3분, `failureReason` 응답 전용(컬럼 없음), 수동 여행
재생성 422, `not_allowed` 서비스 전체 미노출, TourAPI 비저장, 지오코딩 좌표 저장 허용,
`request_text` 백그라운드 LLM 병합.

### 2.4 앱이 깨지는 지점 (명세 리뷰 → 프론트 팀 통보 대상)

- 빈 슬롯 개념이 앱에 없다. `place: null`이면 지금은 직접 입력 항목으로 취급된다 → `slotStatus` 필드 추가와 렌더링 분기 필요.
- `recommendationScore !== null`을 체크 아이콘 조건으로 쓴다 → 확인 필요 후보에도 점수가 있으면 아이콘이 뜬다.
- 상태 폴링 응답에 완성도가 없다 → `GET /routes/{id}/status`에 필드 추가.
- 대안 후보 응답은 기존 `edit-suggestions` 응답 모양(`placeId, name, category, address, primaryImageUrl, recommendationScore, recommendationReason`)을 **재사용**한다. 새 타입을 만들지 않는다.

### 2.5 리뷰어 간 이견과 결정

**(a) 대안 후보 저장: 신규 테이블 vs `route_items` JSONB.**
DB 리뷰는 테이블(조인·FK 무결성·cascade 관례), 설계 리뷰는 JSONB(파생 데이터, 편집 후 무효화되므로
정규화 실익 적음)를 권했다. **테이블로 간다.** 이유: ① 후보를 응답에 내릴 때 어차피 `places`와
조인한다. ② 장소 비활성화·삭제 시 JSONB는 댕글링 참조를 응답 코드가 걸러야 한다. ③ 후속의
"후보 풀 조회"(자유 배치 확장)가 같은 테이블을 읽는다. ④ 팀 관례상 JSONB는 자유 형식에만 쓴다.
무효화 규칙은 설계 리뷰안을 채택: **같은 날짜 안에서 어떤 항목이든 장소가 바뀌면 그 날짜의 후보를
전부 지운다.** 낡은 후보를 보여주는 것보다 없는 편이 낫다.

**(b) 빈 슬롯 표현: `route_items` 행 vs 일자 메타로 응답에만.**
설계 리뷰는 행을 만들면 `_save_itinerary`의 `zip(strict=True)`와 시각 캐스케이드가 깨진다며 응답
메타를 권했다. **행으로 간다.** 이유: ① 빈 슬롯에 붙는 "확인 필요 후보"의 앵커가 필요하다.
② 빈 슬롯을 채우는 동작이 기존 `PUT /route-items/{id}/place`로 그대로 된다. 메타 방식이면 새
엔드포인트가 필요하다. ③ 슬롯의 시간대·유형(저녁 식당 등)을 구조적으로 남겨야 앱이 "17시 식당
자리가 비었어요"를 그릴 수 있다. 설계 리뷰가 지적한 두 코드 위험은 구현 항목으로 처리한다:
이동(`route_moves`)은 **채워진 인접 항목 사이에만** 만들고, 시각 재계산은 빈 슬롯을 건너뛴다.

**(c) 이번 여행 컨디션의 위치: `route_requests` vs `route_request_pets`.**
DB 리뷰안대로 **`route_request_pets`(반려동물별)**로 간다. 여러 마리를 데려갈 때 마리마다 다를 수
있고, 연결 테이블에 스냅샷을 두는 것이 `applied_weights` 패턴과 같다. 앱은 값 하나를 모든
반려동물에 복사해 보내도 된다.

**(d) 음식 종류 컬럼: `category_detail` 재사용 vs 신규 `cuisine`.**
**신규 `cuisine`.** `category_detail`은 모델 주석으로 "etc 세부 분류(동물병원·약국)" 용도가 고정돼
있다. 한 컬럼에 두 분류 축을 섞지 않는다.

---

## 3. 스키마 변경안

### 3.0 변경 없음 (먼저 명확히)

| 항목 | 이유 |
| --- | --- |
| `routes.status` enum | 값 추가 안 함. 부분 성공은 `generated` |
| 완성도(`slotSummary`) | 계산값. `route_items.slot_status` 집계로 응답에만. 출발지·숙소 앵커(체류시간 0)는 제외 (2026-09-08 결정) |
| 실패 사유 | 기존 확정대로 응답 전용 |
| 동물병원 안전망 | 응답 시점 계산. 저장 테이블·PostGIS 없음. 기존 좌표 인덱스로 bounding-box 후 haversine |
| 근거 출처 문장 | `place_pet_policies.source/source_url/verified_at/caution_note` 기존 컬럼 노출 |
| 태그 코드 통일 | DB 무변경. `recommend/config/tags.py`에 코드↔라벨 매핑 |
| 체류시간 기본값 | DB 무변경. 카테고리별 상수(`recommend/config/`). `average_stay_minutes`가 있으면 우선 |
| 환경(`environment`) 추정 | 기존 컬럼 백필 배치. 스키마 무변경 |
| `applied_weights` | 6키 유지. `rating`·`popularity`·`weather` 0 (Phase 5). `healing`·`userCriteria: weather`는 `weather`에 0.10 고정 신호를 남기고 생성기가 `indoor_bias`로 해석 |
| `route_days.weather_snapshot_id` | 이미 있으나 **미사용**. D6 구현 시 채운다 (`weather_snapshots` UNIQUE(region, forecast_at)의 region 정의는 구현 시 결정) |
| 명소 큐레이션 행 | `places` + `place_pet_policies(source='internal', source_url)` 기존 구조. `created_by_user_id`는 NULL 유지 |

### 3.1 `route_items` — 슬롯 상태

```sql
CREATE TYPE route_item_slot_status AS ENUM ('filled', 'unfilled', 'needs_verification');

ALTER TABLE route_items
    ADD COLUMN slot_status route_item_slot_status NOT NULL DEFAULT 'filled';

ALTER TABLE route_items
    ADD CONSTRAINT slot_status_place_consistency CHECK (
        (slot_status = 'unfilled' AND place_id IS NULL AND custom_place_name IS NULL)
        OR (slot_status <> 'unfilled' AND (place_id IS NOT NULL OR custom_place_name IS NOT NULL))
    );
```

| 값 | 뜻 | `place_id` | 시각 |
| --- | --- | --- | --- |
| `filled` | 확실히 동반 가능한 장소로 확정 | 있음 | 있음 |
| `needs_verification` | 정책 unknown 장소로 부족분을 메움. 앱은 "동반 여부 확인 필요" + 전화번호 표시 | 있음 | 있음 |
| `unfilled` | 못 채운 슬롯. `item_type`은 의도한 유형(예: `restaurant`), 후보는 `route_item_candidates`에 | NULL | NULL |

- 기존 행은 전부 `filled` (DEFAULT). 백필 불필요.
- **문서·코드 불일치 정리**: `table-reference.md`는 "`place_id`와 `custom_place_name` 중 하나는 반드시
  존재"라고 적었지만 실제 모델에는 그 CHECK가 없었다. 위 CHECK가 그 규칙을 처음으로 강제한다.
  팀 DB에서 `place_id IS NULL AND custom_place_name IS NULL`인 기존 행이 있는지 확인 후, 있으면
  `NOT VALID` → 정리 → `VALIDATE CONSTRAINT` 순서(`ck_users_local_requires_password` 선례).
- `route_moves`는 `unfilled` 항목을 잇지 않는다. 빈 슬롯 앞 항목의 `moveToNext`는 null.
- 사용자가 `unfilled` 슬롯에 `PUT /route-items/{id}/place`로 장소를 넣으면 `filled` 또는
  `needs_verification`으로 바뀌고 이동·시각을 다시 잇는다.

### 3.2 `route_item_candidates` — 슬롯별 대안 후보 (신규 테이블)

```sql
CREATE TABLE route_item_candidates (
    id                     uuid PRIMARY KEY,
    route_item_id          uuid NOT NULL REFERENCES route_items(id) ON DELETE CASCADE,
    place_id               uuid NOT NULL REFERENCES places(id) ON DELETE CASCADE,
    rank                   smallint NOT NULL,
    recommendation_score   numeric(6,2),
    recommendation_reason  text,
    requires_verification  boolean NOT NULL DEFAULT false,
    created_at             timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT rank_range CHECK (rank BETWEEN 1 AND 3),
    UNIQUE (route_item_id, rank)
);
CREATE INDEX ix_route_item_candidates_place ON route_item_candidates (place_id);
```

- 생성 시 슬롯마다 상위 3개까지. `filled`·`needs_verification` 슬롯의 후보는 "대신 갈 곳",
  `unfilled` 슬롯의 후보는 "확인 필요 후보"(`requires_verification=true`).
- **무효화**: 같은 `route_day` 안에서 항목의 장소가 바뀌거나 순서·추가·삭제가 일어나면 그 날짜
  항목들의 후보를 모두 DELETE. 훅 지점은 `endpoints/route_items.py`의 교체·생성·삭제·순서 변경.
- 재생성(`version` 증가)은 새 `routes` 행을 만들므로 후보도 새로 생긴다. 옛 버전 삭제 시 cascade.
- 응답 필드명: `route_items` 항목에 `candidates: [...]`. 후보 객체는 `edit-suggestions` 응답 모양
  재사용 + `requiresVerification`.

### 3.3 `pets` — 반려동물 여행 특성

```sql
CREATE TYPE pet_activity_level AS ENUM ('low', 'normal', 'high');
CREATE TYPE pet_sociability_level AS ENUM ('low', 'normal', 'high');

ALTER TABLE pets
    ADD COLUMN activity_level pet_activity_level NULL,
    ADD COLUMN sociability    pet_sociability_level NULL,
    ADD COLUMN car_sickness   boolean NULL;   -- NULL = 모름
```

| 컬럼 | 추천 규칙에서의 사용 |
| --- | --- |
| `activity_level` | `low` → 하루 장소 수 −1, 휴식 간격 상향. `high` → 야외·산책 슬롯 우선 |
| `sociability` | `low` → 실내 카페·식당보다 야외 우선, 소규모 장소 선호 (1차 구현에서는 라벨 노출만, 규칙은 후속) |
| `car_sickness` | `true` → 구간 이동시간 상한(예: 40분), 휴식 상향 |
| (기존) `birth_date` | 만 8세 이상 → 하루 장소 수 −1, 연속 이동 상한 |
| (기존) `size`·`weight_kg` | 기존 정책 필터 그대로 |

- 전부 nullable, 기본값 없음. **NULL = 규칙 미적용**. 기존 행 백필 불필요.
- API: `POST/PATCH /pets` 요청·응답에 `activityLevel`, `sociability`, `carSickness` 추가 (`users.md` 갱신).
- `health_notes`는 자유문이라 규칙에 쓰지 않는다.

### 3.4 `route_request_pets` — 이번 여행 컨디션 스냅샷

```sql
CREATE TYPE pet_energy_level AS ENUM ('low', 'normal', 'high');

ALTER TABLE route_request_pets
    ADD COLUMN energy_level pet_energy_level NULL;
```

- 우선순위: `energy_level`(이번 여행) > `pets.activity_level`(기본) > 미적용. README 98~104행의
  "이번 여행 > 기본 취향 > 서비스 기본값" 구조와 같다.
- `pet_activity_level`과 값 집합이 같지만 **별도 enum 타입**으로 둔다. 한쪽만 값을 늘릴 때
  `ALTER TYPE`이 다른 쪽에 번지지 않게.
- API: `POST /route-requests`의 `petIds`를 `pets: [{ petId, energyLevel }]`로 바꾸거나 `petIds`를
  유지하고 `petEnergyLevels: { petId: level }`을 추가. **앱 팀과 협의 후 결정** (요청 바디 변경).

### 3.5 `places` — 음식 종류

```sql
ALTER TABLE places ADD COLUMN cuisine varchar(30) NULL;
```

- 카카오 로컬 `category_name`("음식점 > 한식 > 해물,생선")의 2단계를 정규화해 저장.
  값 집합은 보강 배치에서 확정 (enum화하지 않음. 필터 축이 아니라 표시용).
- 응답: 장소 요약·상세에 `cuisine` 추가 (`places.md` 갱신).
- README 190행 카카오 역할 문장에 "음식 종류(`cuisine`)는 가져온다"를 추가.

### 3.6 `data_provider` enum — 출처 추가 (열린 질문)

명소 좌표·설명을 공공데이터포털(제주도청)에서 가져오면 `description_source`·`place_external_refs.provider`·
`place_pet_policies.source`에 쓸 값이 필요하다. 현재 값: `tour_api, kcisa, visitjeju, kakao, tmap,
weather_api, internal`. 후보: `jeju_open_data`. **출처 목록 확정 후 추가.**

### 3.7 마이그레이션 메모

- 파일 위치는 `apps/api/migrations/versions/`. 현재 head `3d6f8a1b2c4e` 단일.
- enum 생성은 `postgresql.ENUM(..., create_type=False).create(bind, checkfirst=True)`를 `add_column`
  전에, downgrade는 컬럼 drop 후 `enum.drop(checkfirst=True)` (`8c71f4a2d9e0` 선례).
- 모두 additive. 기존 행 안전. `make db-migration-smoke` 필수.
- 마이그레이션은 **하나로 묶지 않는다.** ① `route_items.slot_status` + `route_item_candidates`
  ② `pets` + `route_request_pets` ③ `places.cuisine` 세 개로 나눠 각 Phase에 맞춘다.
- 실서비스 DB(Railway)와 팀 RDS 양쪽 적용은 기존 배치 관례를 따른다.
- **데이터 마이그레이션 `a1f5c9d3e7b2`(Phase 5)**: Phase 5 이전에 만든 `route_requests.applied_weights`는 `weather`가 0.15(옛 기본값)라 재생성 시 `indoor_bias`가 잘못 켜진다. 마이그레이션이 기존 행을 `healing`이면 0.10, 그 외 0으로 바꾸고 6키 합이 1이 되게 재정규화한다(downgrade는 no-op). 변환 로직은 마이그레이션 파일 안에 복사돼 앱 코드와 독립이다.

---

## 4. 기존 결정의 개정 (README 반영 문안)

### 4.1 `docs/database/README.md` 「반려동물 프로필」

> ~~반려동물 성격 태그도 MVP 추천에서 제외합니다.~~
> **(2026-09-07 개정)** 성격 태그 *테이블*은 여전히 만들지 않는다. 대신 추천 규칙에 직접 쓰는
> 여행 특성 3개(`activity_level`, `sociability`, `car_sickness`)를 `pets` 컬럼으로 둔다.
> 이번 여행의 컨디션은 `route_request_pets.energy_level`에 스냅샷한다. 루트 추천의 개인화 중심을
> 사람 취향에서 반려동물로 옮긴 결정(`docs/planning/route-redesign.md`)에 따른 것이다.

「추후 필요할 때만 추가할 테이블」의 "반려동물 성격 태그"는 유지 (테이블은 여전히 안 만든다).

### 4.2 `docs/database/README.md` 「추천 결과와 내 여행」

- `route_items.slot_status`와 `route_item_candidates` 설명 추가.
- 부분 성공: "추천 생성은 채울 수 있는 슬롯만 채우고 나머지는 `unfilled`로 남긴다. `routes.status`는
  여전히 `generated`이며, `failed`는 모든 날이 비었을 때만이다."

### 4.3 「제공처별 역할」 카카오 항목

"긴 소개문·반려동물 조건을 가져오지 않는다"는 유지. "식당의 음식 종류(`cuisine`)는 카카오 로컬
분류에서 가져와 저장한다"를 추가.

---

## 5. API 계약 변경 요약 (추인 후 `routes.md`·`users.md`·`places.md`에 반영)

| 엔드포인트 | 변경 |
| --- | --- |
| `POST /route-requests` | 반려동물별 `energyLevel` 입력 (형태는 앱 팀 협의) |
| `GET /routes/{id}` 항목 | `slotStatus`, `candidates[]`, 장소 요약에 `phone`·`cuisine`·정책 출처(`policySource`, `policySourceUrl`, `policyVerifiedAt`, `cautionNote`) |
| `GET /routes/{id}` 상위 | 완성도(예: `filledCount`, `slotCount`), `nearbyVetClinics[]` (이름은 계약 문서에서 확정) |
| `GET /routes/{id}/status` | 완성도 필드 추가. `failed` 조건 축소 |
| `GET /routes/{id}` 일자 | `weather` 객체 실제 채움 (`weather_snapshot_id` 사용) |
| `recommendationReason` | 의미 변경: 내부 점수 나열 → 동반 조건 + 근거 문장 |
| `POST/PATCH /pets` | `activityLevel`, `sociability`, `carSickness` |
| `routes.md` 216~218행 | "식당 부족 시 실패" → "빈 슬롯 + 확인 필요 후보" 로 개정, 변경 이력 기록 |

---

## 6. 구현 순서 (제안)

| Phase | 내용 | 스키마 |
| --- | --- | --- |
| 0 | 현재 엔진으로 시나리오 매트릭스(권역 4 × 속도 3 × 1~3박) 실패율·슬롯 충족률 측정. 문서 추인. 앱 팀 통보 | — |
| 1 | **긴급**: TMAP 호출 상한 + 직선거리 폴백. 태그 코드 매핑 + 가중치 재조정 (같은 PR) — **구현 완료 2026-09-07** (#263, TMAP 오류 시 여행 단위 추정 폴백 포함. 가중치 반려 .45 · 근접 .25 · 취향 .20 · 날씨 .10). **1b 완료**: 추정식 `7분 + 직선÷600m/min`(TMAP 실측 38구간 MAPE 34%→17%, 한라산 배율은 실측상 불필요), 상한은 실제 호출만 카운트, 상세 응답 `isEstimated` 폴백 | — |
| 2 | 데이터 보강 (병렬): 명소 큐레이션, 카테고리별 체류시간, 환경 백필, 카테고리 오염 정리, 카카오 음식 종류 — **구현 완료 2026-09-08** (#268, 명소 28곳·정책 갱신 3곳, DB 적용은 보류) | ③ `cuisine` |
| 3 | 부분 성공 + tier: 후보 3값(`VERIFIED/NEEDS_CHECK/BLOCKED`), 하드 실패 제거, 빈 슬롯 행, 후보 저장, 완성도 응답 — **구현 완료 2026-09-08** (#269, Phase 2 위 스택 브랜치. 식사 슬롯 미충족은 어떤 경로든 빈 슬롯 기록, 후보 응답 `phone`) | ① `slot_status` + `route_item_candidates` |
| 4 | 반려동물 중심 개인화: `applied_weights` 하위호환, pets 컬럼, `pet_score(candidate, pets, condition)`, 속도 규칙 보정, 이동시간 상한 완화 단계 — **구현 완료 2026-09-08** (#270, 스택. 컨디션이 활동량을 덮어씀, 차멀미 상한은 숙소 복귀 구간 포함, 사회성은 저장만) | ② `pets` + `route_request_pets` |
| 5 | 하루 구성 규칙: 기상청 날짜별 예보(기온 포함), 슬롯 계획(`plan_day`) 도입, `build` 분해, `weather_snapshot_id` 채움 — **구현 완료 2026-09-08** (#271, 스택. 임계값 60/80%·30℃, `itinerary` 패키지 분해, `SlotSearchContext`·`Rung`) | — |
| 6 | 근거 문장 템플릿 + 출처 노출, LLM 여행 설명 1회, 동물병원 안전망 모듈 | — |
| 7 | 여유 시: `regenerate` 엔드포인트(명세만 있고 미구현), `route_recommendation.py` 분해 | — |

시연이 임박하면 Phase 4~5를 자른다. **자를 수 없는 것은 1(지연), 2(데이터), 3(부분 성공)**이다.

---

## 7. 열린 질문

1. `POST /route-requests`의 반려동물별 컨디션 입력 형태 (앱 팀).
2. `data_provider`에 추가할 출처 값 (공공데이터포털 사용 확정 시).
3. 24시 동물병원 판정을 `place_business_hours`로 할 수 있는지 실데이터 확인. 안 되면 이름·설명 문자열.
4. `weather_snapshots` UNIQUE(region, forecast_at)에서 좌표 기반 저장 시 `region` 정의. → **확정(Phase 5)**: 기상청 5km 격자 키 `kma:{nx},{ny}`, `forecast_at`은 그날 00:00 KST.
5. 명소 큐레이션 목록 초안 검토자.
6. Phase 5에서 `weather` 축을 빼면서 `healing` 프리셋과 `userCriteria: weather`를 하루 구성 규칙(실내 비중 상향)으로 어떻게 재정의할지. 앱의 선택지 문구도 함께 조정. → **확정(Phase 5)**: `applied_weights.weather` 0.10 고정 신호 → `indoor_bias` → 80% 비 규칙 강제. 앱 문구는 앱 팀.
7. 가입 화면 취향 선택지(`vibeOptions`)와 `place_tags.code` 7종의 어휘 통일 (앱 팀, 우선순위 낮음).
8. Phase 3 슬롯 계획에 날짜별 **권역**(제주시/서귀포/동부/서부) 배정을 넣을지. 산 횡단을 구조적으로 줄이는 유일한 방법.
