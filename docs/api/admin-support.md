# 관리자 고객지원 콘솔 API

작성일: 2026-09-08 · 상태: **구현됨**

공통 규약은 [`README.md`](./README.md)를 따른다. 관리자 인증·권한 설정은
[`editorial-stories.md`](./editorial-stories.md) "관리자 권한 설정"과 같다 —
모든 요청이 access token과 `users.is_admin=true` 를 요구하고, 일반 사용자는 403이다.

관련 테이블: `inquiries`, `notices`, `admin_inquiry_audit_logs`, `admin_notice_audit_logs`

---

## 1:1 문의

### 사용자 API (신규 구현)

스펙은 [`notifications.md`](./notifications.md) "1:1 문의"에 확정돼 있고, 이번에 구현했다.

| Method | Path | 설명 |
| --- | --- | --- |
| GET | `/api/v1/inquiries?status=&limit=&offset=` | 내 문의 목록 (목록은 `content`·`answer`·`imageUrls` 생략) |
| POST | `/api/v1/inquiries` | 문의 작성 — `status`는 서버가 `pending` 으로 고정, 201 |
| GET | `/api/v1/inquiries/{inquiryId}` | 내 문의 상세 (다른 사용자 문의는 403) |

문의는 작성 후 수정·삭제할 수 없다. 카테고리 코드는 `account` `pet` `saved` `schedule` `bug` `etc`.
첨부 이미지는 `POST /uploads` (`purpose=inquiry`)로 먼저 받은 주소만, 최대 5개.

### 관리자 API

| Method | Path | 설명 |
| --- | --- | --- |
| GET | `/api/v1/admin/inquiries` | 전체 문의 목록. `status`·`category` 필터, `search`(제목 부분일치), `sortBy=created_at\|answered_at`, `order`, `page`/`limit` |
| GET | `/api/v1/admin/inquiries/{inquiryId}` | 상세 — 문의자(`asker`) 정보와 최근 30건 변경 이력 포함 |
| POST | `/api/v1/admin/inquiries/{inquiryId}/answer` | 답변 등록 — body `{ "answer": "..." }` |
| POST | `/api/v1/admin/inquiries/{inquiryId}/draft-answer` | AI 답변 초안 생성 (저장 안 함) |

**답변 편집기 초기값 (템플릿)** — 상세 응답의 `answerTemplate` 이 편집기에 채워질 초기값이다:

```
{문의자 닉네임}님, 안녕하세요.
오멍가멍입니다.

<빈 본문>

감사합니다.
오멍가멍 드림
```

머릿말은 문의자 닉네임으로 개인화한다(닉네임이 비면 "고객"). **관리자가 인사말·맺음말
포함 전체를 자유롭게 수정할 수 있다.** `POST .../answer` 의 `answer` 는 관리자가 보낸
**전체 텍스트**이고, 서버는 감싸지 않고 그대로 저장한다. `draft-answer` 의 `reply` 는
인사말·맺음말이 붙은 완성된 초안이다(모델은 본문만 만들고 서버가 조립).

**답변 등록** 시:
- 관리자가 보낸 답변 전체(strip만)와 `answered_at`(현재 시각)·`status="completed"` 를 저장한다 (DB CHECK `completed_has_answer`).
- `admin_inquiry_audit_logs` 에 `action="answered"` 한 줄을 남긴다.
- 문의자에게 `type="inquiry_answered"` 알림을 만들고 푸시한다 — 단 `users.inquiry_answer_notification_enabled=false` 인 사용자는 제외.
- 이미 `completed` 인 문의에 다시 답변하면 **409**.

**AI 답변 초안** (`/draft-answer`):
- 임베딩 없이 DB 조회로만 맥락을 모은다 — ① 같은 카테고리의 과거 답변된 문의 3건, ② 문의 제목·본문 키워드로 찾은 여행 가이드 문서, ③ 서비스 기본 사실.
- OpenAI 를 1회 호출해(`inquiry_openai_model` 또는 `openai_model`) 답변 본문을 만든다. 응답: `{ reply, usedContext, needsHumanReview, model }`.
- `needsHumanReview=true` 는 "맥락만으로는 확실히 답하기 어렵다"는 모델의 표시다. 관리자가 사실 확인 후 보낸다.
- `OPENAI_API_KEY` 미설정 → **503**, LLM 호출 실패 → **502**. 초안은 어떤 것도 DB에 저장하지 않는다. 완료된 문의는 **409**.

---

## 공지사항

사용자 조회 API(`GET /notices`)는 기존 그대로다([`notifications.md`](./notifications.md)).

### 관리자 API

| Method | Path | 설명 |
| --- | --- | --- |
| GET | `/api/v1/admin/notices` | 전체 목록(초안·비활성·미래 포함). `filter=all\|announced\|draft`, `search`, `page`/`limit` |
| GET | `/api/v1/admin/notices/{noticeId}` | 상세 + 최근 30건 이력 |
| POST | `/api/v1/admin/notices` | 초안 생성 — `is_active=false` 로 저장, 알림 없음, 201 |
| PATCH | `/api/v1/admin/notices/{noticeId}` | 수정 — `title`/`content`/`isPinned`/`isActive`/`publishedAt`. **알림을 다시 보내지 않는다.** |
| POST | `/api/v1/admin/notices/{noticeId}/publish` | 발행 — `is_active=true`, 전 사용자 알림·푸시 **1회** |
| POST | `/api/v1/admin/notices/{noticeId}/unpublish` | 게시 중단 — `is_active=false` |

### 발행과 1회성 알림

`notices.announced_at` 이 "알림을 이미 보냈다"는 표식이다.

| 상태 | `announced_at` | `is_active` | 사용자 앱 노출 |
| --- | --- | --- | --- |
| 초안 | `NULL` | `false` | ✗ |
| 게시 중 | 값 있음 | `true` | ✓ (`published_at <= now` 조건) |
| 게시 중단 | 값 있음 | `false` | ✗ |

- `/publish` 는 `announced_at IS NOT NULL` 이면 **409** — 두 번 발송되지 않는다.
- 게시 중단 후 다시 보이려면 `PATCH { "isActive": true }` — 조용히 다시 노출되며 알림은 안 간다.
- `announced_at` 은 게시 중단해도 지우지 않는다. 그래서 재발송은 영구히 불가능하다.
- 마이그레이션이 기존 공지에 `announced_at = published_at` 을 백필한다(이미 과거에 발송된 것으로 간주).

`v1` 에는 공지 삭제(`DELETE`)가 없다.

---

## 변경 이력

| 날짜 | 내용 |
| --- | --- |
| 2026-09-08 | 초안 작성 — 사용자 `/inquiries` 구현, 관리자 문의 답변·AI 초안·공지 CRUD, `notices.announced_at`, 도메인별 감사 로그 |
