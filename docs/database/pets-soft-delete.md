# 반려동물 프로필 soft delete 및 기록 스냅샷 설계 메모

향후 ERD 작성과 실제 DB 연동을 위한 설계 메모다. 이번 작업 범위는 프론트 타입 · Mock Service ·
화면 연결까지이며, 실제 마이그레이션은 만들지 않았다.

## 배경

반려동물 프로필을 지워도 과거 여행 기록은 그대로 남아야 한다. 기록에서 반려동물 태그가 사라지거나
기록 자체가 삭제되면 사용자가 잃는 것이 너무 크다. 그래서 두 가지를 정책으로 못 박았다.

1. 프로필 삭제는 물리 삭제가 아니라 `status = 'deleted'`로 바꾸는 soft delete
2. 기록에는 저장 시점의 반려동물 정보를 스냅샷으로 복사해 보관

## 테이블

```text
pets
- pet_id            PK
- user_id           FK
- name
- species           '강아지' | '고양이'
- breed
- age
- weight
- profile_image_url NULLABLE
- status            'active' | 'deleted'
- deleted_at        NULLABLE
- created_at
- updated_at
```

```text
travel_log_pets
- travel_log_id              FK
- pet_id                     FK NULLABLE, ON DELETE SET NULL
- pet_name_snapshot
- pet_profile_image_snapshot NULLABLE
```

```text
trip_pets
- trip_id                    FK
- pet_id                     FK NULLABLE, ON DELETE SET NULL
- pet_name_snapshot
- pet_profile_image_snapshot NULLABLE
```

`trip_pets`는 `travel_log_pets`와 같은 스냅샷 컬럼을 갖는다. 여행(Trip)은 로그가 하나도 없어도
존재할 수 있는 독립 단위라 하위 로그에서 계산하지 않고 별도 행으로 보관한다.

## 제약과 이유

- **`pet_id`는 nullable, `ON DELETE SET NULL`**: 향후 정책이 바뀌어 프로필을 물리 삭제하더라도
  기록의 스냅샷 이름·사진은 남아야 한다. 스냅샷 컬럼이 있으므로 `pet_id`가 NULL이 되어도 화면은 그대로 그려진다.
- **`name`에 unique 제약을 걸지 않는다**: 같은 이름의 반려동물을 여러 마리 키울 수 있고,
  지운 뒤 같은 이름으로 다시 등록할 수도 있다. 이때 둘은 서로 다른 개체다.
- **동일 개체 판단은 항상 `pet_id`**: 이름 · 종 · 품종 · 사진은 판단 근거가 될 수 없다.
  이름은 중복되고 언제든 바뀔 수 있기 때문이다.
- **재등록은 언제나 새 `pet_id` 발급**: 같은 이름의 삭제된 행을 복원하거나 재사용하지 않는다.

## 조회 규칙

- 마이페이지 목록, 새 여행 코스 · 새 기록의 반려동물 선택: `status = 'active'`만
- 과거 기록의 필터 옵션: 전체(`active` + `deleted`). 지워진 항목은 "이름 · 이전 프로필"로 구분해 노출
- 기록 카드의 반려동물 태그: `pet_id`로 `pets` 행을 찾아 **현재 이름 · 사진**을 표시

## 표시 이름 정책

이름과 사진은 화면에 그릴 때마다 `pet_id`로 `pets` 행을 조회해 최신 값을 쓴다. `pet_id`는 절대 바뀌지
않는 불변 식별자이므로 이름이 바뀌어도 연결 관계는 그대로다. soft delete라 프로필을 지워도 행이 남아
있어 과거 기록의 태그가 사라지지 않는다.

스냅샷 컬럼은 `pets` 행 자체를 찾지 못할 때(향후 물리 삭제로 `pet_id`가 NULL이 되는 경우 등)의
fallback으로만 쓴다. 필터 옵션도 같은 규칙을 따르며, 한 반려동물이 이름을 여러 번 바꿨을 때
기록마다 다른 `pet_name_snapshot`이 남아 어느 것을 고를지 정할 수 없다는 점도 같은 이유다.

fallback 판단은 컬럼 단위가 아니라 **행 단위**다. `pets` 행을 찾았다면 `profile_image_url`이 NULL이어도
스냅샷으로 되돌아가지 않는다. 그렇지 않으면 사진을 기본 이미지로 되돌렸을 때 과거 기록에만 지운 사진이
계속 남는다.

## 현재 프론트 대응

| 설계 | 구현 위치 |
| --- | --- |
| `pets` 테이블 | `src/types/pet.ts`의 `Pet`, `src/features/profile/services/petService.ts` |
| `travel_log_pets` | `TravelLog.companions: TravelLogPetSnapshot[]` |
| `trip_pets` | `Trip.companions: TravelLogPetSnapshot[]` |
| soft delete | `petService.deletePet` (배열에서 제거하지 않고 status만 변경) |
| 활성/전체 조회 분리 | `petService.fetchPets` / `fetchAllPets` |
| 필터 옵션 | `src/features/travel-logs/utils/petFilterOptions.ts` |
| 표시 이름 해석 | `src/features/travel-logs/utils/resolveCompanionDisplay.ts` |

API 연동 시에는 `petService`의 함수 본문만 apiClient 호출로 교체하면 되고, 화면과 타입은 그대로 쓸 수 있다.
