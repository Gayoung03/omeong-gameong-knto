# 제주 여행 이야기

홈의 `제주 여행 이야기`는 비짓제주 공식 Open API 콘텐츠를 매주 월요일 골라 AI 초안으로
바꾼 뒤 `editorial_stories`에 저장한다. 비짓제주 대표사진 URL과 원문 링크만 보관하며
수집한 원문 전체는 DB에 저장하지 않는다.

## 운영 흐름

```text
Railway Cron (매주 월요일 09:00 KST)
→ scripts.sync_editorial_stories
→ 비짓제주 API 조회 → OpenAI로 4종(행사·날씨·이야기·가이드) 초안 생성
→ editorial_stories 에 draft 저장
→ apps/admin 검수함(/stories, 기본 draft)에서 검수·수정·저장
→ 관리자 승인(POST /admin/editorial-stories/{id}/publish) — 즉시 게시
→ GET /editorial-stories (published 만) → 모바일 홈
```

생성 책임은 Cron에, 게시 책임은 관리자 승인 API에만 있다.

## 휴먼 인 더 루프

- AI(OpenAI)는 **주간 초안을 쓰는 단계에만** 쓴다.
- 검증·수정·승인은 운영자가 관리자 웹에서 직접 한다. 수정 화면과 수정 API
  (`PATCH /admin/editorial-stories/{id}`)에는 LLM 호출이 없다(AI 다시 쓰기·자동 교정 없음).
  운영자가 저장한 값이 그대로 게시된다.
- 운영자 확인 항목: 비짓제주 원문 대조(출처 카드), 날짜·운영시간·반려동물 허용 같은 사실,
  말투, 사진.
- 수정·게시·보관·초안 복귀는 모두 감사 이력에 남는다.

본문 편집은 `소제목 · 본문 · 사진` 묶음을 글 흐름대로 이어 붙이는 방식이다. 본문 한 칸에서
빈 줄로 문단을 나누고, 저장할 때 `sections[].paragraphs` 배열로 바뀐다. API·모바일 데이터
형식은 그대로다.

## 환경변수

```dotenv
VISITJEJU_API_KEY=
OPENAI_API_KEY=
EDITORIAL_OPENAI_MODEL=gpt-4o-mini
WEATHER_API_KEY=
```

## 주간 배치 (매주 월요일)

```bash
cd apps/api
uv run python -m scripts.sync_editorial_stories        # 로컬
.venv/bin/python -m scripts.sync_editorial_stories     # 컨테이너(Railway)
```

- **draft만 만든다.** 배치에는 게시(`published`)를 만드는 옵션·코드 경로가 없다.
- **같은 주 재실행에 안전하다.** 기준일은 실행한 날이 속한 주의 **KST 월요일**이다.
  slug `{월요일}-{kind}-{원문id}`의 앞부분(`{월요일}-{kind}-`)으로 그 주 종류별 존재 여부를 본다.
  - 이미 있는 종류는 비짓제주 상세 조회·OpenAI 호출 **전에** 건너뛴다. 4종이 모두 있으면
    비짓제주 목록 조회도 하지 않는다.
  - 상태(draft/published/archived)와 무관하게 "이미 있음"으로 본다. 원문 후보나 날씨가
    바뀌어도 같은 주 같은 종류는 추가되지 않는다.
  - 기존 행은 어떤 필드도 수정하지 않는다. 관리자 수정·승인 내용이 유지된다.
- 종류마다 저장 후 commit한다. 한 종류의 OpenAI 호출이 실패해도 다른 종류는 남고,
  같은 주 안에 다시 실행하면(수요일이어도) 빠진 종류만 생성한다.
- 결과 로그: `YYYY-MM-DD 생성 N · 건너뜀 M · 실패 K`. 실패가 있으면 종료 코드 1,
  없으면 0으로 정상 종료한다.
- 날씨 카드는 **초안을 만든 날**의 다음 KST 자정에 만료된다. 월요일에 만든 날씨 초안은
  월요일 안에 승인해야 하며, 넘기면 만료 시각을 늦춰 저장한 뒤 승인한다.

## 관리자 승인 규칙

- 수정과 승인은 `draft`에서만 가능하다(아니면 409).
- 승인은 **즉시 게시**다. `published_at`은 서버가 승인 시각으로 정하고, 요청 바디의
  게시 시각은 받지 않는다(예약 게시 없음).
- **같은 종류 교체**: 승인하면 같은 종류로 게시 중인 기존 글을 같은 트랜잭션에서
  `archived`로 바꾸고, 감사 이력(`archived`, `changes.replaced_by`)을 남긴 뒤 새 글을 게시한다.
- 같은 종류 승인은 `pg_advisory_xact_lock`으로 직렬화한다. 동시에 승인해도 뒤 요청이
  앞 요청의 게시 글을 보관하므로 종류별 게시 글은 최대 1건이다.
- 만료 시각이 이미 지난 초안은 승인할 수 없다(422). 만료 시각을 늦춰 저장하거나
  다음 날 초안을 승인한다.
- 게시 글을 고치려면 `published → archived → draft → published` 순서로 전환한다.

## 공개 API

- `GET /api/v1/editorial-stories?limit=4`
- `GET /api/v1/editorial-stories/{storyId}`

`published`이면서 게시 시각이 지났고 만료되지 않은 글만 반환한다(목록·상세 공통).
draft·archived는 절대 노출하지 않는다. 종류별 게시 글이 최대 1건이므로 `limit=4`가
과거 같은 종류 글로 채워지지 않는다. 모바일은 이 목록 API를 그대로 사용한다.

## 관리자 API

모든 요청은 access token과 `users.is_admin=true` 권한을 모두 요구한다.
일반 로그인 사용자는 403을 받는다.

- `GET /api/v1/admin/me`: 관리자 세션 확인
- `GET /api/v1/admin/editorial-stories?status=draft&sortBy=collected_at` — 검수함,
  `total`이 미검수 초안 수(관리자 사이드바 배지)
- `GET /api/v1/admin/editorial-stories/{storyId}`
- `PATCH /api/v1/admin/editorial-stories/{storyId}`
- `POST /api/v1/admin/editorial-stories/{storyId}/publish`
- `POST /api/v1/admin/editorial-stories/{storyId}/archive`
- `POST /api/v1/admin/editorial-stories/{storyId}/draft`

게시·보관·초안 복귀와 수정 필드는 `admin_editorial_audit_logs`에 남는다.

## Railway Cron 서비스 등록

API 서비스 안의 스케줄러가 아니라 **별도 Cron 서비스**에서 실행한다. 등록하지 않으면
매주 자동 생성되지 않는다.

1. Railway 프로젝트에서 **New → GitHub Repo** → 같은 저장소 선택.
2. 새 서비스 **Settings → Source → Root Directory**: `apps/api` (기존 Dockerfile로 빌드).
3. **Settings → Deploy → Custom Start Command**:
   `.venv/bin/python -m scripts.sync_editorial_stories`
   (컨테이너의 bare `python`에는 의존성이 없다.)
4. **Settings → Cron Schedule**: `0 0 * * 1`
   Railway Cron은 **UTC 기준** → UTC 월요일 00:00 = 매주 **월요일 09:00 KST**.
   실행 시각은 몇 분 늦어질 수 있다.
5. **Networking**: 공개 도메인을 만들지 않는다.
6. **Variables** — API 서비스 값을 참조로 공유한다(서비스 이름이 다르면 바꿔 적는다).

   ```text
   DATABASE_URL=${{omeong-gameong-knto.DATABASE_URL}}
   SECRET_KEY=${{omeong-gameong-knto.SECRET_KEY}}
   VISITJEJU_API_KEY=${{omeong-gameong-knto.VISITJEJU_API_KEY}}
   OPENAI_API_KEY=${{omeong-gameong-knto.OPENAI_API_KEY}}
   EDITORIAL_OPENAI_MODEL=${{omeong-gameong-knto.EDITORIAL_OPENAI_MODEL}}
   WEATHER_API_KEY=${{omeong-gameong-knto.WEATHER_API_KEY}}
   ENVIRONMENT=production
   ```

7. **종료 조건**: 이전 실행이 끝나지 않으면 Railway가 다음 실행을 건너뛴다. 스크립트는
   DB 세션(`with SessionLocal()`)과 HTTP 클라이언트를 닫고 정상 종료하도록 작성돼 있다.

### 수동 재실행

```bash
railway ssh            # API 서비스 선택
.venv/bin/python -m scripts.sync_editorial_stories
```

같은 주(월~일)면 빠진 종류만 생성하고 나머지는 건너뛴다.

### 성공 확인

- Cron 서비스 실행 로그의 마지막 줄이 `생성 N · 건너뜀 M · 실패 0`이고 프로세스가 종료됨
- 다음 날 실행이 skip 없이 기록됨(Cron 서비스 배포 이력)
- 관리자 웹 사이드바 "여행 이야기" 배지와 `/stories` 검수함에 그날 draft가 보임

### 완료 체크리스트

| 구분 | 항목 |
| --- | --- |
| 코드 | 배치 draft 전용·재실행 안전, 승인 교체 규칙, 공개 API 경계, 관리자 검수함 |
| 운영(대시보드) | Cron 서비스 생성, Start Command, Cron Schedule, Variables, 첫 실행 로그 확인 |

## 관리자 권한 설정

먼저 일반 회원가입을 완료한 계정에 권한을 부여한다.

```bash
cd apps/api
uv run python -m scripts.manage_admin grant --email admin@example.com
uv run python -m scripts.manage_admin revoke --email admin@example.com
```

운영 환경에서는 실수 방지를 위해 `--confirm-production`을 함께 입력해야 한다.
로컬 `seed_dev` 는 관리자 웹 확인용 계정 `admin@omeong.local`(nickname 관리자)을
따로 심는다. 시드 사용자 `seed@omeong.local`(율무)은 일반 사용자다.
