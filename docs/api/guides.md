# 여행 가이드 API

작성일: 2026-08-12 · 갱신: 2026-08-30 · 상태: **구현**

공통 규약은 [`README.md`](./README.md)를 따릅니다.

관련 DB 테이블:

- `guide_documents`
- `guide_document_sources`
- `transport_pet_rules`
- `transport_restricted_breeds`

---

## 기능

반려동물과 제주 여행을 준비할 때 필요한 항공사·여객선 탑승 규정과 공통 준비 가이드를 제공합니다.

앱의 여행 준비 가이드 화면은 다음 데이터를 사용합니다.

- 항공사별 기내·위탁 가능 여부
- 기내·위탁 무게 제한
- 국내선 요금
- 신청 마감·온라인 체크인 제한
- 여객선 항로·소요 시간·동반 조건
- 출처와 확인일
- 출발 전 공통 체크리스트

---

## 엔드포인트

```text
GET /api/v1/guides
GET /api/v1/guides/{guideSlug}
GET /api/v1/guides/transport-rules
GET /api/v1/guides/transport-rules/{ruleId}
```

### `GET /api/v1/guides`

가이드 문서 목록을 조회합니다. 비활성 문서는 내려주지 않습니다.

쿼리:

| 이름 | 타입 | 설명 |
| --- | --- | --- |
| `category` | `airline` \| `ferry` \| `preparation` | 선택 시 해당 분류만 조회 |
| `limit` | number | 기본 20, 최대 100 |
| `offset` | number | 기본 0 |

응답 예시:

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "slug": "prep-packing",
      "title": "반려동물 제주 여행 준비물",
      "category": "preparation",
      "summary": "이동 전 준비해야 할 물품을 정리합니다.",
      "verifiedAt": "2026-08-27T00:00:00+09:00",
      "sources": [
        {
          "sourceName": "공식 안내",
          "sourceUrl": "https://example.com",
          "sourceNote": null,
          "verifiedAt": "2026-08-27T00:00:00+09:00"
        }
      ]
    }
  ],
  "total": 15,
  "limit": 20,
  "offset": 0
}
```

### `GET /api/v1/guides/{guideSlug}`

가이드 문서 상세를 조회합니다. 목록 응답 필드에 `body`가 추가됩니다.

### `GET /api/v1/guides/transport-rules`

항공사·여객선별 반려동물 운송 규정을 조회합니다.

쿼리:

| 이름 | 타입 | 설명 |
| --- | --- | --- |
| `carrierType` | `airline` \| `ferry` | 선택 시 운송수단 분류로 필터 |
| `q` | string | 운송사명, 항로, 문서 제목 검색 |
| `limit` | number | 기본 50, 최대 100 |
| `offset` | number | 기본 0 |

응답 주요 필드:

| 이름 | 설명 |
| --- | --- |
| `carrierName` | 항공사 또는 선사명 |
| `carrierType` | `airline` 또는 `ferry` |
| `route` | 여객선 항로. 항공사는 보통 `null` |
| `cabinAllowed` | 기내·객실 동반 가능 여부 |
| `cabinMaxWeightKg` | 기내·객실 무게 제한 |
| `cargoAllowed` | 위탁 운송 가능 여부 |
| `cargoMaxWeightKg` | 위탁 무게 제한 |
| `cabinFeeKrw` | 국내선 기내 요금 |
| `requestDeadlineHours` | 사전 신청 마감 시간 |
| `durationMinutes` | 여객선 소요 시간 |
| `notes` | 주의사항과 보충 설명 |
| `sources` | 공식 출처 목록 |

### `GET /api/v1/guides/transport-rules/{ruleId}`

운송 규정 상세를 조회합니다. 존재하지 않거나 연결된 문서가 비활성 상태면 404를 반환합니다.

---

## 앱 연결

모바일 앱은 [`guidesApi.ts`](../../apps/mobile/src/features/travel-guides/api/guidesApi.ts)에서 위 API를 읽고,
[`TravelPreparationScreen.tsx`](../../apps/mobile/src/features/travel-guides/screens/TravelPreparationScreen.tsx)와
[`TravelGuideDetailScreen.tsx`](../../apps/mobile/src/features/travel-guides/screens/TravelGuideDetailScreen.tsx)에 표시합니다.

체크리스트 항목은 앱 안에서 공통 준비 흐름으로 유지하고, 운송사별 규정과 준비 가이드 문서는 DB 응답을 사용합니다.

---

## 확인 방법

루트에서 전체 개발 서버를 띄운 뒤 앱에서 여행 준비 가이드 화면을 엽니다.

```bash
make dev
```

API만 확인할 때는 다음 요청을 사용합니다.

```bash
curl http://localhost:8000/api/v1/guides
curl http://localhost:8000/api/v1/guides/transport-rules
curl 'http://localhost:8000/api/v1/guides/transport-rules?carrierType=airline'
```

---

## 변경 이력

| 날짜 | 내용 |
| --- | --- |
| 2026-08-12 | 초안 작성. 대응 DB 테이블 부재로 설계 보류 상태 기록 |
| 2026-08-18 | 기능 성격 확정 — 반려동물과 여행할 때 도움이 되는 정보를 모아 보는 곳 |
| 2026-08-30 | DB 기반 가이드 문서·운송 규정 API 구현 및 모바일 여행 준비 가이드 화면 연결 |
