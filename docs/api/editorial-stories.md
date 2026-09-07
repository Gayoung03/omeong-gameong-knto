# 제주 여행 이야기

홈의 `제주 여행 이야기`는 비짓제주 공식 Open API 콘텐츠를 매일 골라 AI 초안으로
바꾼 뒤 `editorial_stories`에 저장한다. 비짓제주 대표사진 URL과 원문 링크만 보관하며
수집한 원문 전체는 DB에 저장하지 않는다.

## 환경변수

```dotenv
VISITJEJU_API_KEY=
OPENAI_API_KEY=
EDITORIAL_OPENAI_MODEL=gpt-4o-mini
```

## 수집과 게시

```bash
cd apps/api
uv run python -m scripts.sync_editorial_stories
```

기본 실행은 `draft` 네 건만 만든다. 관리자 웹에서 원문·이미지·말투를
확인하고 수정한 뒤 승인해야 한다.

```bash
uv run python -m scripts.sync_editorial_stories --publish
```

Railway Scheduled Job에는 첫 번째 명령을 하루 한 번 등록한다. `--publish`는
관리자 검수를 우회하므로 예외적인 수동 복구 외에는 사용하지 않는다.

## 공개 API

- `GET /api/v1/editorial-stories?limit=4`
- `GET /api/v1/editorial-stories/{storyId}`

`published`이면서 게시 시각이 지났고 만료되지 않은 글만 반환한다. 날씨 카드는 다음 날
자정에 자동 만료된다.

## 관리자 API

모든 요청은 access token과 `users.is_admin=true` 권한을 모두 요구한다.
일반 로그인 사용자는 403을 받는다.

- `GET /api/v1/admin/me`: 관리자 세션 확인
- `GET /api/v1/admin/editorial-stories?status=draft&sortBy=collected_at`
- `GET /api/v1/admin/editorial-stories/{storyId}`
- `PATCH /api/v1/admin/editorial-stories/{storyId}`
- `POST /api/v1/admin/editorial-stories/{storyId}/publish`
- `POST /api/v1/admin/editorial-stories/{storyId}/archive`
- `POST /api/v1/admin/editorial-stories/{storyId}/draft`

수정은 `draft`에서만 가능하다. 게시물을 고치려면
`published → archived → draft → published` 순서로 전환한다. 게시·보관·초안
복귀와 수정 필드는 `admin_editorial_audit_logs`에 남는다.

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
