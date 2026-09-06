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

기본 실행은 `draft` 네 건만 만든다. 관리자 페이지가 완성되기 전 사람이 내용을 직접
확인한 경우에만 아래 명령으로 해당 날짜의 네 건을 게시한다.

```bash
uv run python -m scripts.sync_editorial_stories --publish
```

Railway Scheduled Job에는 첫 번째 명령을 하루 한 번 등록한다. 관리자 화면은 나중에
`draft` 조회·수정과 `published` 전환만 연결하면 된다.

## 공개 API

- `GET /api/v1/editorial-stories?limit=4`
- `GET /api/v1/editorial-stories/{storyId}`

`published`이면서 게시 시각이 지났고 만료되지 않은 글만 반환한다. 날씨 카드는 다음 날
자정에 자동 만료된다.
