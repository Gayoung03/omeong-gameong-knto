# KCISA 장소 데이터 품질 감사

- 감사일: 2026-08-30
- 대상: 현재 공유 DB에서 `place_external_refs.provider = 'kcisa'`로 연결된 장소
- 범위: 데이터 조회와 분류만 수행했으며 DB 데이터는 변경하지 않음
- 기준 시점: 2026-08-29 권역 정정 작업 반영 이후

## 1. 결론

KCISA 연결 장소는 총 **544곳**이며 활성 516곳, 비활성 28곳이다.

| 항목 | 결과 |
| --- | ---: |
| 주소와 `region`의 명백한 시 단위 불일치 | 0곳 |
| 숙소로 오인할 수 있는 이름이지만 비숙소 카테고리인 장소 | 2곳 |
| `etc` 카테고리 | 278곳 |
| 이미지 없음 | 497곳 (91.4%) |
| `not_allowed` 정책 | 87곳 |
| 원본 `동반 가능정보=N`과 DB 정책 불일치 | 0곳 |

KCISA에 포함된 장소를 모두 반려동물 동반 가능 장소로 간주하면 안 된다. 원본이
`동반 가능정보=N`인 87곳은 DB에서도 모두 `not_allowed`로 유지되고 있으며, 이 값을
허용 정책으로 바꿀 근거는 없다.

## 2. 감사 방법

KCISA 장소는 `places.description_source`가 아니라 아래 연결을 기준으로 식별했다.
한 장소에 여러 제공처가 합쳐질 수 있으므로 설명 출처만으로 KCISA 여부를 판단하면
누락될 수 있다.

```sql
FROM places p
JOIN place_external_refs r ON r.place_id = p.id
WHERE r.provider = 'kcisa'
```

집계 쿼리는 `SELECT`만 실행했으며 세션 종료 전 `ROLLBACK`했다. DB 호스트, 사용자명,
비밀번호 등 연결 정보는 결과와 문서에 남기지 않았다.

## 3. 전체 분포

### 활성 상태

| 상태 | 장소 수 |
| --- | ---: |
| 활성 | 516 |
| 비활성 | 28 |
| 합계 | 544 |

비활성 28곳의 활성화 여부는 데이터 품질 감사와 별도 운영 결정이다. 이번 감사에서는
변경하지 않았다.

### 현재 카테고리

| 카테고리 | 장소 수 |
| --- | ---: |
| `etc` | 278 |
| `attraction` | 129 |
| `accommodation` | 65 |
| `pet_service` | 32 |
| `cafe` | 21 |
| `veterinary_hospital` | 9 |
| `beach` | 4 |
| `restaurant_cafe` | 3 |
| `oreum` | 2 |
| `walking_trail` | 1 |
| 합계 | 544 |

### 현재 지역

| `region` | 장소 수 |
| --- | ---: |
| `제주시/제주국제공항` | 227 |
| `서귀포시/모슬포` | 125 |
| `애월/한림/협재` | 85 |
| `함덕/김녕/세화` | 45 |
| `표선/성산` | 43 |
| `중문` | 19 |
| 합계 | 544 |

## 4. 주소와 `region` 불일치

다음 두 가지 명백한 역전만 자동 판정 대상으로 삼았다.

1. 주소가 서귀포시인데 `region`이 서귀포 권역 3종이 아닌 경우
2. 주소가 제주시인데 `region`이 `서귀포시/모슬포`, `표선/성산`, `중문`인 경우

현재 해당 장소는 **0곳**이다. 2026-08-29 권역 정정 이후 최소한의 행정구역 정합성은
맞아 있다.

이 결과가 세부 관광권역까지 모두 정확하다는 뜻은 아니다. 예를 들어 남원읍 장소를
`서귀포시/모슬포`, `표선/성산`, `중문` 중 어디에 둘지는 행정구역 문자열만으로 확정할
수 없다. 이런 세부 배분은 좌표 또는 팀의 권역 기준을 확인하는 수동 검토 항목이다.

## 5. 숙소명과 카테고리

숙소를 암시할 수 있는 문자열
`펜션|게스트하우스|호텔|리조트|민박|스테이|캠핑|카라반`이 이름에 포함됐지만
`accommodation`이 아닌 KCISA 장소는 2곳이다.

| 장소 | 현재 카테고리 | KCISA 원본 분류 | 판정 |
| --- | --- | --- | --- |
| 스테이솔티 | `attraction` | 반려동반여행 > 여행지 | 수동 검토 |
| 오멍가멍 애견카페&호텔 | `restaurant_cafe` | 반려동물식당카페 > 카페 | 현행 유지 |

- **스테이솔티**: 이름만 보면 숙소처럼 보이지만 KCISA 원본은 여행지다. 실제 영업 형태를
  확인하기 전에는 자동으로 숙소로 변경하지 않는다.
- **오멍가멍 애견카페&호텔**: 원본이 카페이고 이름의 호텔은 반려동물 호텔 서비스를
  뜻할 가능성이 높다. 사람의 숙박시설인 `accommodation`으로 바꾸지 않는다.

기존 정정 스크립트에 기록된 숙소 4곳은 현재 이미 `accommodation`으로 반영되어 이번
후보에서 제외됐다. 앞으로도 이름만으로 카테고리를 자동 변경하지 않는다.

## 6. `etc` 카테고리 감사

`etc`는 278곳으로 KCISA 장소의 51.1%다. 그러나 원본 분류가 사라진 것은 아니며
`places.description`의 `[KCISA 원본 분류]`에 다음과 같이 보존돼 있다.

| KCISA 원본 하위 분류 | 장소 수 | 현재 판단 |
| --- | ---: | --- |
| 동물약국 | 126 | 별도 카테고리 정책 필요 |
| 동물병원 | 75 | `veterinary_hospital` 자동 정정 가능 |
| 반려동물용품 | 51 | `pet_service` 자동 정정 가능 |
| 미용 | 26 | `pet_service` 자동 정정 가능 |
| 합계 | 278 | |

동물병원·용품·미용은 장소 이름 추측이 아니라 KCISA의 구조화된 원본 분류를 근거로
정정할 수 있다. 반면 동물약국 126곳은 현재 서버 카테고리 체계에 대응 값이 없다.
`veterinary_hospital`이나 `pet_service`에 임의로 합치지 말고, `animal_pharmacy` 같은
새 코드 도입 여부를 먼저 결정해야 한다.

## 7. 이미지 감사

`primary_image_url`이 `NULL` 또는 빈 문자열인 장소는 497곳이다.

| 카테고리 | 이미지 없음 | 전체 |
| --- | ---: | ---: |
| `etc` | 278 | 278 |
| `attraction` | 113 | 129 |
| `accommodation` | 57 | 65 |
| `pet_service` | 24 | 32 |
| `cafe` | 21 | 21 |
| `beach` | 2 | 4 |
| `oreum` | 1 | 2 |
| `walking_trail` | 1 | 1 |
| `restaurant_cafe` | 0 | 3 |
| `veterinary_hospital` | 0 | 9 |
| 합계 | 497 | 544 |

이미지 누락은 값만으로 자동 수정할 수 없다. KCISA 원본 또는 사용 허가가 확인된 다른
제공처의 이미지 URL을 확보한 뒤 외부 ID·주소로 동일 장소임을 검증해야 한다. 임의의
검색 이미지나 크롤링 이미지는 넣지 않는다.

## 8. 동반 정책 감사

KCISA 장소 544곳 모두 `place_pet_policies.source = 'kcisa'`인 정책 행을 가지고 있다.

| DB 정책 | 장소 수 |
| --- | ---: |
| `indoor_allowed` | 309 |
| `outdoor_only` | 80 |
| `partial_allowed` | 68 |
| `not_allowed` | 87 |
| 합계 | 544 |

정책 `notes`에서 가장 마지막 `반려동물 동반 가능정보: Y/N` 값을 원본 KCISA 값으로
읽어 DB 정책과 비교했다. 기존 정책과 KCISA 정책이 함께 있는 행은 마지막 KCISA 구간을
사용해 과거 값이 비교에 섞이지 않게 했다.

| 원본 값 | DB 정책 | 장소 수 |
| --- | --- | ---: |
| `N` | `not_allowed` | 87 |
| `Y` | `indoor_allowed` | 309 |
| `Y` | `outdoor_only` | 80 |
| `Y` | `partial_allowed` | 68 |

- 원본 표식 보존: 544/544
- 원본 `N`: 87곳
- `N`인데 허용 정책인 장소: **0곳**
- 원본 `Y`인데 `not_allowed`인 장소: **0곳**

따라서 현재 `동반 가능정보=N`과 DB 정책은 모두 일치한다. `not_allowed` 87곳은 검색과
추천의 기본 후보에서 계속 제외해야 한다.

## 9. 자동 수정 가능 항목과 수동 검토 항목

### 자동 수정 가능

자동 수정은 별도 작업에서 미리보기, 대상 ID 기록, 롤백 경로, 테스트를 갖춘 뒤 진행한다.
이 문서 작성 과정에서는 실행하지 않았다.

| 항목 | 근거 | 예상 대상 |
| --- | --- | ---: |
| `etc` 동물병원 → `veterinary_hospital` | KCISA 원본 하위 분류가 동물병원 | 75 |
| `etc` 반려동물용품 → `pet_service` | KCISA 원본 하위 분류가 반려동물용품 | 51 |
| `etc` 미용 → `pet_service` | KCISA 원본 하위 분류가 미용 | 26 |

현재 주소·권역 불일치와 원본 `N` 정책 불일치는 0건이므로 이 두 항목에 적용할 자동
수정은 없다.

### 수동 검토 또는 정책 결정 필요

| 항목 | 이유 |
| --- | --- |
| `etc` 동물약국 126곳 | 대응 서버 카테고리 코드가 없음 |
| 스테이솔티 | 이름과 KCISA 원본 분류가 다르게 보임 |
| 오멍가멍 애견카페&호텔 | 호텔이 사람 숙소인지 반려동물 서비스인지 이름만으로 판단 불가 |
| 이미지 누락 497곳 | 사용 권한과 동일 장소 검증이 필요 |
| 세부 관광권역 | 행정구역 문자열만으로 관광권역을 확정할 수 없음 |
| 비활성 KCISA 장소 28곳 | 활성화는 운영 노출 범위를 바꾸는 별도 결정 |

## 10. 재현용 읽기 쿼리

### KCISA 장소와 이미지 수

```sql
SELECT
  count(DISTINCT p.id) AS total,
  count(DISTINCT p.id) FILTER (
    WHERE nullif(btrim(p.primary_image_url), '') IS NULL
  ) AS missing_images
FROM places p
JOIN place_external_refs r ON r.place_id = p.id
WHERE r.provider = 'kcisa';
```

### `etc` 원본 분류

```sql
SELECT
  substring(
    p.description FROM '\[KCISA 원본 분류\][^\n]*> ([^\n]+)'
  ) AS source_leaf,
  count(DISTINCT p.id) AS count
FROM places p
JOIN place_external_refs r ON r.place_id = p.id
WHERE r.provider = 'kcisa'
  AND p.category = 'etc'
GROUP BY source_leaf
ORDER BY count DESC;
```

### 원본 `Y/N`과 DB 정책 비교

```sql
WITH matches AS (
  SELECT
    p.id,
    pp.policy_type::text AS policy,
    m.value[1] AS raw_value,
    m.ord
  FROM places p
  JOIN place_external_refs r ON r.place_id = p.id
  JOIN place_pet_policies pp ON pp.place_id = p.id
  CROSS JOIN LATERAL regexp_matches(
    coalesce(pp.notes, ''),
    '반려동물 동반 가능정보:[[:space:]]*([YN])',
    'g'
  ) WITH ORDINALITY AS m(value, ord)
  WHERE r.provider = 'kcisa'
), latest AS (
  SELECT DISTINCT ON (id) id, policy, raw_value
  FROM matches
  ORDER BY id, ord DESC
)
SELECT raw_value, policy, count(*) AS count
FROM latest
GROUP BY raw_value, policy
ORDER BY raw_value, policy;
```

## 11. 후속 권고

1. 원본 분류가 명확한 `etc` 152곳(동물병원 75, 용품 51, 미용 26)은 별도 데이터
   정정 작업으로 분리한다.
2. 동물약국 126곳은 서버·모바일 카테고리 코드를 먼저 합의한다.
3. 이미지 보강은 제공처 이용 조건과 출처 기록 방식을 정한 뒤 진행한다.
4. 스테이솔티만 실제 업종을 수동 확인한다. 오멍가멍 애견카페&호텔은 현재 원본 분류를
   우선해 유지한다.
5. `동반 가능정보=N` 87곳은 임의로 허용 처리하지 않는다.
