# 리뷰 API

작성일: 2026-08-12 · 상태: **확정 규약 반영** (2026-08-12 팀 회의)

공통 규약은 [`README.md`](./README.md)를 따릅니다.

관련 DB 테이블: `reviews`, `review_images`

---

## 엔드포인트 목록

| Method | Path | 설명 | 인증 |
| --- | --- | --- | --- |
| GET | `/places/{placeId}/reviews` | 장소별 리뷰 목록 | 선택 |
| POST | `/places/{placeId}/reviews` | 리뷰 작성 | 필요 |
| GET | `/users/me/reviews` | 내가 쓴 리뷰 목록 | 필요 |
| PATCH | `/reviews/{reviewId}` | 리뷰 수정 | 필요 |
| DELETE | `/reviews/{reviewId}` | 리뷰 삭제 | 필요 |

리뷰는 **물리 삭제**입니다. `reviews` 테이블에 `deleted_at`이 없어
`users`·`pets`와 달리 soft delete 대상이 아닙니다. 따라서 응답에 `status` 필드도 없습니다.

---

## GET /places/{placeId}/reviews

### 요청

```text
GET /api/v1/places/{placeId}/reviews?limit=20&offset=0&sort=recent
```

| 파라미터 | 기본값 | 설명 |
| --- | --- | --- |
| `sort` | `recent` | `recent` `ratingHigh` `ratingLow` |
| `limit` | 20 | 최대 100 |
| `offset` | 0 | |

### 응답 `200`

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "rating": 5,
      "content": "산책로가 넓어서 강아지랑 다니기 좋았어요.",
      "petPolicyAccurate": true,
      "visitedAt": "2026-07-15",
      "images": [
        { "imageUrl": "https://...", "sortOrder": 0 },
        { "imageUrl": "https://...", "sortOrder": 1 }
      ],
      "author": {
        "nickname": "여행자",
        "profileImageUrl": "https://..."
      },
      "pet": {
        "name": "몽이",
        "species": "dog",
        "size": "small"
      },
      "isMine": false,
      "createdAt": "2026-07-16T09:12:00+09:00",
      "updatedAt": "2026-07-16T09:12:00+09:00"
    }
  ],
  "total": 37,
  "limit": 20,
  "offset": 0,
  "summary": {
    "averageRating": 4.3,
    "totalCount": 37,
    "ratingDistribution": { "5": 20, "4": 10, "3": 5, "2": 1, "1": 1 },
    "petPolicyAccurateRate": 0.89
  }
}
```

### 필드 설명

| 필드 | 설명 |
| --- | --- |
| `rating` | 1~5. DB CHECK 제약과 동일 |
| `petPolicyAccurate` | 등록된 동반 정책이 실제와 맞았는지. `null` 가능 |
| `visitedAt` | **날짜**(`2026-07-15`). 시각이 아님 |
| `author` | `users` 조인 결과. 사용자 ID는 노출하지 않음 |
| `pet` | 함께 간 반려동물. `pet_id`가 `null`이면 이 필드도 `null` |
| `isMine` | 계산값. 비로그인이면 `false` |
| `summary` | 계산값. 목록 응답에 함께 담아 화면이 한 번에 그림 |

> **`visitedAt` 주의** — 같은 이름이지만 `travel_logs.visited_at`은 **시각**입니다.
> 리뷰는 날짜만 받습니다. 앱에서 같은 형식으로 다루면 안 됩니다.

리뷰 작성자가 탈퇴했거나 반려동물을 삭제한 경우에도 리뷰는 남습니다.
탈퇴한 사용자의 `author.nickname`을 어떻게 표시할지는 아래 확인 필요 항목 참고.

> **[확인 필요]** 탈퇴 사용자의 리뷰 표시 방법.
> `reviews.user_id`는 `ON DELETE CASCADE`이지만 실제 삭제는 soft delete라 행이 남습니다.
> 닉네임을 그대로 보일지 "탈퇴한 사용자"로 바꿀지 정해야 합니다.

---

## POST /places/{placeId}/reviews

### 요청

```json
{
  "rating": 5,
  "content": "산책로가 넓어서 강아지랑 다니기 좋았어요.",
  "petPolicyAccurate": true,
  "visitedAt": "2026-07-15",
  "petId": "550e8400-e29b-41d4-a716-446655440000",
  "imageUrls": [
    "https://...",
    "https://..."
  ]
}
```

| 필드 | 필수 | 제약 |
| --- | --- | --- |
| `rating` | ✅ | 1 ~ 5 |
| `content` | — | |
| `petPolicyAccurate` | — | |
| `visitedAt` | — | 날짜. 미래 날짜 불가 |
| `petId` | — | 본인 소유여야 함. 삭제된 반려동물도 지정 가능 |
| `imageUrls` | — | 순서대로 `sortOrder` 0부터 저장 |

`imageUrls`의 배열 순서가 그대로 `review_images.sort_order`가 됩니다.
`(review_id, sort_order)`에 UNIQUE 제약이 있어 중복 순서는 저장되지 않습니다.

`imageUrls`에 담을 주소는 [`uploads.md`](./uploads.md)의 `POST /uploads`로 미리 받습니다
(`purpose`는 `review`). 사진을 한 장씩 올려 받은 `fileUrl`을 순서대로 배열에 담아 보냅니다.

```text
POST /uploads (1장째)  → fileUrl A
POST /uploads (2장째)  → fileUrl B
POST /places/{placeId}/reviews   { "imageUrls": [A, B] }
```

### 응답 `201`

`GET /places/{placeId}/reviews`의 항목 하나와 동일한 구조입니다.

### 에러

| 코드 | 상황 |
| --- | --- |
| 403 | 다른 사용자의 `petId` |
| 404 | 없는 `placeId` |
| 422 | `rating` 범위 초과, 미래 `visitedAt` |

> **[확인 필요]** 같은 장소에 리뷰를 여러 번 쓸 수 있는지.
> DB에 `(user_id, place_id)` UNIQUE 제약이 없어 현재는 중복 작성이 가능합니다.
> 1인 1리뷰로 제한하려면 서버에서 막고 `409`를 돌려줘야 합니다.

---

## GET /users/me/reviews

내가 쓴 리뷰 목록입니다. 마이페이지에서 씁니다.

### 응답 `200`

장소별 목록과 같은 항목 구조에 `place` 요약이 추가되고 `author`는 빠집니다.

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "rating": 5,
      "content": "산책로가 넓어서 강아지랑 다니기 좋았어요.",
      "visitedAt": "2026-07-15",
      "images": [{ "imageUrl": "https://...", "sortOrder": 0 }],
      "place": {
        "id": "...",
        "name": "함덕해수욕장",
        "primaryImageUrl": "https://..."
      },
      "createdAt": "2026-07-16T09:12:00+09:00"
    }
  ],
  "total": 4,
  "limit": 20,
  "offset": 0
}
```

기본 정렬은 `createdAt` 최신순입니다.

---

## PATCH /reviews/{reviewId}

보낸 필드만 수정합니다.

### 요청

```json
{
  "rating": 4,
  "content": "수정된 내용",
  "imageUrls": ["https://..."]
}
```

`imageUrls`를 보내면 **기존 이미지를 전부 지우고 새로 저장**합니다.
개별 이미지만 빼는 방식은 지원하지 않습니다. 화면이 항상 전체 목록을 제출하기 때문입니다.

`placeId`와 `petId`는 수정할 수 없습니다. 장소를 잘못 골랐다면 삭제 후 다시 작성합니다.

### 에러

| 코드 | 상황 |
| --- | --- |
| 403 | 다른 사용자의 리뷰 |
| 404 | 없는 `reviewId` |
| 422 | `rating` 범위 초과 |

---

## DELETE /reviews/{reviewId}

물리 삭제입니다. `review_images`도 `ON DELETE CASCADE`로 함께 지워집니다.

### 응답 `204`

본문 없음.

### 에러

| 코드 | 상황 |
| --- | --- |
| 403 | 다른 사용자의 리뷰 |
| 404 | 없는 `reviewId` |

삭제하면 장소의 `reviewCount`와 `rating`이 다시 계산됩니다. 저장된 값이 아니라 조회 시 집계입니다.

---

## 변경 이력

| 날짜 | 내용 |
| --- | --- |
| 2026-08-12 | 초안 작성 |
| 2026-08-12 | 이미지 업로드 확인 필요 항목을 [`uploads.md`](./uploads.md) 참조로 교체 |
