# 이미지 업로드 API

작성일: 2026-08-12 · 상태: **확정 — 2026-08-12 결정**

공통 규약은 [`README.md`](./README.md)를 따릅니다.

관련 DB 테이블: **없음**

이미지 파일 자체는 DB에 저장하지 않습니다. 파일은 스토리지에 두고,
DB에는 그 주소(URL) 문자열만 저장합니다.

> **이 결정은 2026-08-12 팀 회의 안건이 아니었습니다.**
> 회의에서 확정한 10개 항목과 달리, 이 문서는 명세서 점검 중 발견된 공백을 메우려고
> 같은 날 별도로 정한 내용입니다. **팀 공유와 추인이 필요합니다.**

---

## 이 문서가 필요한 이유

여러 도메인 문서가 이미지 주소를 **받는다**고 이미 전제하고 있었습니다.

| 문서 | 필드 | 필수 |
| --- | --- | --- |
| [`travel-logs.md`](./travel-logs.md) | `originalImageUrl` | ✅ |
| [`reviews.md`](./reviews.md) | `imageUrls` | — |
| [`notifications.md`](./notifications.md) | `imageUrls` (문의) | — |
| [`users.md`](./users.md) | `profileImageUrl` | — |
| [`users.md`](./users.md) | `imageUrl` (반려동물) | — |
| [`places.md`](./places.md) | `primaryImageUrl` | — |

그런데 **그 주소를 만들어내는 엔드포인트가 어디에도 없었습니다.**

앱은 갤러리에서 고른 사진의 로컬 경로(`file:///...`)만 갖고 있습니다.
이를 `https://` 주소로 바꿀 방법이 없으면 위 6개 기능이 전부 막힙니다.

특히 `travel_logs.original_image_url`은 **NOT NULL**이라
(`apps/api/app/db/models/community.py:120`) 사진 없이는 기록 자체를 만들 수 없습니다.

---

## 엔드포인트 목록

| Method | Path | 설명 | 인증 |
| --- | --- | --- | --- |
| POST | `/uploads` | 이미지 파일 업로드 | 필요 |

---

## 왜 도메인 API와 분리하는가

리뷰 작성 요청이 사진 파일을 직접 받게 만들 수도 있습니다.
그렇게 하지 않는 이유는 세 가지입니다.

**하나.** 같은 일을 6곳에서 반복하게 됩니다. 업로드 규칙(크기·형식·에러)이 바뀔 때마다
6개 문서와 6개 엔드포인트를 모두 고쳐야 합니다.

**둘.** 요청 형식이 섞입니다. 파일을 직접 받으면 `multipart/form-data`가 되어,
[`reviews.md`](./reviews.md)·[`travel-logs.md`](./travel-logs.md)에 적힌 JSON 예시가 전부 무효가 됩니다.

**셋.** 나중에 업로드 방식을 바꿀 때 도메인 API가 함께 흔들립니다.
분리해 두면 이 문서 하나만 고치면 됩니다(아래 마이그레이션 경로 참고).

```text
분리한 구조

POST /uploads          파일 → URL          ← 이 문서
POST /reviews          URL을 받아 저장      ← 기존 명세 그대로
POST /travel-logs      URL을 받아 저장      ← 기존 명세 그대로
```

---

## POST /uploads

### 요청

**이 엔드포인트만 JSON이 아닙니다.** `multipart/form-data`로 보냅니다.

```text
POST /api/v1/uploads
Content-Type: multipart/form-data
Authorization: Bearer <accessToken>
```

| 파트 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `file` | file | ✅ | 이미지 파일 1개 |
| `purpose` | string | ✅ | 용도. 아래 표 참고 |

**요청 하나당 파일 하나입니다.** 리뷰처럼 사진을 여러 장 올릴 때는
앱이 이 요청을 반복 호출하고, 받은 `fileUrl`을 모아 배열로 만듭니다.

한 번에 여러 파일을 받지 않는 이유는, 일부만 실패했을 때 처리가 복잡해지기 때문입니다.
한 장씩 올리면 실패한 것만 다시 시도하면 됩니다.

### 응답 `201`

```json
{
  "fileUrl": "https://storage.example.com/review/2026/08/550e8400-e29b-41d4-a716-446655440000.jpg",
  "contentType": "image/jpeg",
  "sizeBytes": 284913
}
```

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `fileUrl` | string | 도메인 API에 그대로 전달할 주소 |
| `contentType` | string | 서버가 실제로 판별한 형식 |
| `sizeBytes` | int | 저장된 파일 크기 |

`fileUrl`은 **인증 없이 접근 가능한 공개 주소**입니다.
파일명은 서버가 UUID로 새로 만듭니다. 원본 파일명을 그대로 쓰면
한글·공백·중복 문제가 생기고, 사용자가 올린 이름이 URL에 노출됩니다.

### purpose

용도를 함께 받는 이유는 저장 경로를 나누고, 용도별로 제약을 다르게 두기 위해서입니다.

| 값 | 쓰는 곳 | 최종 저장 위치 |
| --- | --- | --- |
| `review` | 리뷰 사진 | `review_images.image_url` |
| `travel_log` | 여행기록 원본 사진 | `travel_logs.original_image_url` |
| `inquiry` | 문의 첨부 | `inquiries.image_urls` |
| `profile` | 사용자 프로필 | `users.profile_image_url` |
| `pet` | 반려동물 사진 | `pets.image_url` |
| `place` | 나만의 장소 대표 사진 | `places.primary_image_url` |

목록에 없는 값은 `422`입니다.

`travel_logs.generated_image_url`(AI가 만든 이미지)은 이 목록에 없습니다.
서버가 생성해 직접 저장하므로 앱이 업로드하지 않습니다.

### 제약

```text
허용 형식     image/jpeg  image/png  image/webp
파일 크기     10MB 이하
```

형식은 **파일 내용을 검사해 판별합니다.** 확장자나 클라이언트가 보낸 `Content-Type`을
그대로 믿지 않습니다. `.jpg`로 이름만 바꾼 실행 파일을 막기 위해서입니다.

> **[확인 필요] — iPhone HEIC 형식.**
> iOS 기본 카메라 형식은 HEIC입니다. Expo `ImagePicker`가 보통 JPEG로 변환해 주지만,
> 설정에 따라 HEIC가 그대로 올라올 수 있습니다.
> 앱에서 변환할지, 서버가 HEIC를 허용하고 변환할지 정해야 합니다.

> **[확인 필요] — 크기 상한 수치.**
> 위 10MB는 제안값입니다. 여행기록은 AI 이미지 생성 입력으로 쓰이므로
> 화질 요구사항이 정해지면 용도별로 다르게 둘 수도 있습니다.

### 에러

| 코드 | 상황 |
| --- | --- |
| 401 | 토큰 없음·만료 |
| 413 | 파일 크기 초과 |
| 415 | 허용하지 않는 형식 |
| 422 | `file` 또는 `purpose` 누락, 알 수 없는 `purpose` |
| 500 | 스토리지 저장 실패 |

`413`과 `415`는 이 엔드포인트에서만 쓰입니다.
[`README.md`](./README.md) 4장 상태 코드 표에 함께 정리되어 있습니다.

---

## 앱에서의 흐름

리뷰에 사진 2장을 올리는 경우입니다.

```text
갤러리에서 2장 선택
  → POST /uploads (1장째)  → fileUrl A
  → POST /uploads (2장째)  → fileUrl B
  → POST /places/{placeId}/reviews
       { "rating": 5, "imageUrls": [A, B] }
```

업로드가 끝나야 리뷰 작성 요청을 보낼 수 있습니다.
사진이 여러 장이면 화면에 진행 상태를 보여주는 편이 좋습니다.

**업로드만 하고 도메인 요청을 보내지 않으면 파일이 스토리지에 남습니다.**
사용자가 사진을 고른 뒤 작성을 취소한 경우가 여기 해당합니다.
정리 정책은 아래 확인 사항에 있습니다.

### 업로드 함수로 감싸기 (권장)

앱은 업로드를 **함수 하나로 감싸서** 쓰기를 권합니다.

```ts
// 예시
async function uploadImage(localUri: string, purpose: UploadPurpose): Promise<string> {
  // multipart 요청을 보내고 fileUrl만 돌려준다
}
```

각 화면은 이 함수만 부르고, 업로드가 내부적으로 몇 번의 요청으로 이뤄지는지 모르게 합니다.
이렇게 해두면 나중에 업로드 방식이 바뀌어도 **이 함수 하나만 고치면 됩니다.**
리뷰 화면·프로필 화면·기록 작성 화면은 손대지 않아도 됩니다.

---

## 나중에 앱이 직접 올리는 방식으로 바꿀 때

지금은 서버가 파일을 받아 스토리지에 저장합니다.
트래픽이 늘면 앱이 스토리지에 직접 올리는 방식(presigned URL)으로 바꿀 수 있습니다.

그때 달라지는 것은 아래가 전부입니다.

| 대상 | 영향 |
| --- | --- |
| 이 문서 | 응답에 `uploadUrl` 추가, 흐름 2단계 → 3단계 |
| 서버 `/uploads` 내부 | 저장 로직 → 허가증 발급 로직 |
| 앱 `uploadImage()` | 요청 1번 → 2번 |
| **도메인 API 6개** | **없음** |
| **도메인 문서 6개** | **없음** |

```text
바뀐 뒤의 흐름

POST /uploads          → { uploadUrl, fileUrl }
PUT  <uploadUrl>       → 스토리지에 파일 직접 전송
POST /reviews          → { imageUrls: [fileUrl] }
```

도메인 API가 `imageUrls`에 주소 문자열을 받는다는 계약은 양쪽이 동일하므로
영향을 받지 않습니다.

**단, 이미 올라간 파일은 따로 옮겨야 합니다.** 서버 로컬 디스크에 저장하다가
외부 스토리지로 바꾸는 경우입니다. 실사용 데이터가 쌓이기 전에 결정할수록 비용이 작습니다.

---

## 남은 확인 사항

| 항목 | 내용 |
| --- | --- |
| 스토리지 제공처 | S3 · Cloudflare R2 · 서버 로컬 디스크 중 미정. 현재 저장소에 관련 설정·의존성 없음 |
| 크기 상한 수치 | 10MB는 제안값 |
| HEIC 처리 | 앱 변환 / 서버 변환 / 거부 |
| 안 쓰인 파일 정리 | 업로드 후 도메인 요청이 오지 않은 파일을 언제 지울지 |
| 삭제 시 파일 처리 | 리뷰·기록을 지울 때 스토리지 파일도 지울지 ([`travel-logs.md`](./travel-logs.md) 확인 사항과 동일 안건) |

`apps/api/app/core/config.py`에는 현재 `database_url`과 `cors_origins`만 있습니다.
스토리지를 정하면 설정값 추가가 필요합니다.

---

## 변경 이력

| 날짜 | 내용 |
| --- | --- |
| 2026-08-12 | 초안 작성. 6개 도메인에 걸친 업로드 엔드포인트 부재를 메움 |
