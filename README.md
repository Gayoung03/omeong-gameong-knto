# 오멍가멍

2026 관광데이터 활용 공모전 출품을 위한 반려동물 동반 제주 여행 플래너입니다.

## 기술 스택

- 모바일: React Native, Expo SDK 57, Expo Router, TypeScript
- 상태 관리: Zustand, TanStack Query
- 폼 및 통신: React Hook Form, Zod, Axios
- 백엔드: FastAPI, SQLAlchemy 2, Alembic
- 데이터베이스: PostgreSQL 16, pgvector
- Python 환경 및 잠금: uv
- Node 패키지 및 잠금: npm, package-lock.json

## 사전 준비

- Node.js 22 LTS
- npm
- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- Docker Desktop
- 모바일 테스트용 Expo Go

Node 버전은 저장소 루트의 `.nvmrc`, Python 버전은
`apps/api/.python-version`을 기준으로 맞춥니다.

## 최초 설치

저장소를 clone한 후 루트에서 환경변수 파일을 만듭니다.

```bash
cp .env.example .env
make setup
```

`make setup`은 다음 작업을 수행합니다.

- `apps/mobile`: `package-lock.json` 기준 npm 패키지 설치
- `apps/api`: `uv.lock` 기준 Python 가상환경 및 패키지 설치

`.venv`를 직접 활성화할 필요 없이 `uv run` 또는 Makefile 명령을 사용합니다.

## 실행

저장소 루트에서 다음 명령 하나로 PostgreSQL, DB 마이그레이션, FastAPI, Expo를 동시에 실행합니다.

```bash
make dev
```

종료할 때는 `Ctrl+C`를 누릅니다. Expo와 FastAPI가 함께 종료되고 PostgreSQL
컨테이너도 자동으로 종료됩니다. PostgreSQL 데이터 볼륨은 삭제되지 않습니다.

`make dev`는 PostgreSQL이 준비될 때까지 기다린 뒤 `alembic upgrade head`를 실행하므로,
팀원마다 동일한 최신 테이블 구조가 자동으로 적용됩니다.

- FastAPI: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/api/v1/health`
- Expo: 터미널에 표시되는 QR 코드를 Expo Go로 스캔

필요한 경우 각 서비스를 따로 실행할 수도 있습니다.

```bash
make db-up
make db-migrate
make api-dev
make mobile-dev
```

실제 휴대폰에서 API를 호출할 때는 `.env`의 `EXPO_PUBLIC_API_URL`에 컴퓨터의
같은 Wi-Fi 내부 IP를 지정해야 합니다.

```dotenv
EXPO_PUBLIC_API_URL=http://192.168.0.10:8000/api/v1
```

`localhost`는 휴대폰 자신을 의미하므로 실제 기기에서는 사용할 수 없습니다.

## 검사

PR을 만들기 전에 루트에서 실행합니다.

```bash
make check
```

개별 명령도 사용할 수 있습니다.

```bash
make lint
make typecheck
make test
```

## 주요 폴더

```text
apps/mobile  React Native + Expo 프론트엔드
apps/api     FastAPI 백엔드
packages     공통 설정과 생성 API 클라이언트
infra        PostgreSQL 등 로컬 인프라
docs         기획, 화면, API, 데이터베이스 문서
```

화면 라우트는 `apps/mobile/app`, 실제 기능 코드는
`apps/mobile/src/features`에 작성합니다.

## 의존성 변경 규칙

### 모바일

일반 패키지:

```bash
cd apps/mobile
npm install <package-name>
```

Expo 네이티브 패키지:

```bash
cd apps/mobile
npx expo install <package-name>
```

변경된 `package.json`과 `package-lock.json`을 함께 커밋합니다.

### API

```bash
cd apps/api
uv add <package-name>
```

개발 전용 패키지는 다음과 같이 추가합니다.

```bash
uv add --dev <package-name>
```

변경된 `pyproject.toml`과 `uv.lock`을 함께 커밋합니다.

## 주의 사항

- `.env`, `.venv`, `node_modules`는 Git에 올리지 않습니다.
- 팀 합의 없이 패키지를 추가하거나 버전을 변경하지 않습니다.
- `package-lock.json`과 `uv.lock`을 삭제하지 않습니다.
- 각자 별도의 Expo 프로젝트를 만들지 않고 이 저장소에서 작업합니다.
- 공통 라우팅, 테마, 공용 컴포넌트 수정 전 팀에 공유합니다.
