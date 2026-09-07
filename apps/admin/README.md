# 오멍가멍 관리자 웹

운영 콘솔 React + Vite SPA입니다. 현재 메뉴:

- **여행 이야기** — 비짓제주 초안 검수·수정·게시
- **1:1 문의** — 사용자 문의 확인·답변 (답변 시 AI 초안 생성)
- **공지사항** — 공지 작성·수정·발행 (발행 시 전 사용자 알림 1회)
- 품질 검증 — 다음 작업 (비활성)

API 스펙: [editorial-stories.md](../../docs/api/editorial-stories.md), [admin-support.md](../../docs/api/admin-support.md)

## 로컬 실행

FastAPI와 로컬 DB를 먼저 준비한 뒤 실행합니다.

```bash
make backend-local-up
SEED_DEV_PASSWORD=<로컬비밀번호> make db-seed-local
make admin-dev
```

`http://localhost:5173`에 접속해 **`admin@omeong.local`** 과 위 `SEED_DEV_PASSWORD`
값으로 로그인합니다. (`seed@omeong.local` = 율무는 일반 사용자라 로그인하면 403.
문의를 남기는 쪽 계정입니다.) 다른 API를 사용하려면 `.env`를 만듭니다.

```bash
cp .env.example .env
```

## Vercel 배포

기존 모바일 웹 프로젝트와 별도의 Vercel 프로젝트로 연결합니다.

- Git 저장소: 기존과 동일
- Production Branch: `main`
- Root Directory: `apps/admin`
- Framework Preset: Vite
- Build Command: `npm run build`
- Output Directory: `dist`
- Environment Variable: `VITE_API_BASE_URL=https://<api-domain>/api/v1`

SPA 상세 URL에서 새로고침해도 접속되도록 `vercel.json`의 rewrite를 포함한다.
배포 URL이 정해지면 FastAPI의 `CORS_ORIGINS` JSON 배열에 관리자 웹
오리진을 추가해야 한다.

## 권한

관리자 화면은 일반 로그인 API로 access token을 받은 뒤 `/admin/me`로
DB의 현재 권한을 다시 확인한다. token은 브라우저 탭의 `sessionStorage`에만
보관하며 탭을 닫으면 사라진다.

관리자 권한 부여·회수 명령은
[editorial-stories API 문서](../../docs/api/editorial-stories.md#관리자-권한-설정)를 참고합니다.
