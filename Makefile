COMPOSE = docker compose --env-file .env -f infra/docker-compose.yml
LOCAL_COMPOSE = $(COMPOSE) -f infra/docker-compose.local.yml
REHEARSAL_COMPOSE = docker compose -f infra/docker-compose.rehearsal.yml

.PHONY: setup dev dev-local mobile-install api-install mobile-dev api-dev backend-up \
	backend-down backend-logs backend-local-up backend-local-down backend-local-logs \
	db-migrate db-migrate-check db-migrate-local db-seed db-seed-local \
	db-migration-smoke db-dump-dev db-rehearsal-up db-rehearsal-restore \
	db-rehearsal-migrate db-rehearsal-down chat-check chat-check-places \
	chat-check-guardrails \
	lint typecheck test check

setup: mobile-install api-install

dev: backend-up
	@trap 'cd "$(CURDIR)" && $(COMPOSE) down --remove-orphans' EXIT; \
	cd apps/mobile && npx concurrently \
		--kill-others \
		--names MOBILE,API-LOGS \
		--prefix-colors cyan,magenta \
		"npm run dev" \
		"cd ../.. && $(COMPOSE) logs -f api"

dev-local: backend-local-up
	@trap 'cd "$(CURDIR)" && $(LOCAL_COMPOSE) down --remove-orphans' EXIT; \
	cd apps/mobile && npx concurrently \
		--kill-others \
		--names MOBILE,API-LOGS \
		--prefix-colors cyan,magenta \
		"npm run dev" \
		"cd ../.. && $(LOCAL_COMPOSE) logs -f api"

mobile-install:
	cd apps/mobile && npm ci

api-install:
	cd apps/api && uv sync --frozen

mobile-dev:
	cd apps/mobile && npm run dev

api-dev:
	$(COMPOSE) up --build api

backend-up:
	$(COMPOSE) up --build -d --wait --remove-orphans api

backend-down:
	$(COMPOSE) down --remove-orphans

backend-logs:
	$(COMPOSE) logs -f api

backend-local-up: db-migrate-local
	$(LOCAL_COMPOSE) up --build -d --wait --remove-orphans api

backend-local-down:
	$(LOCAL_COMPOSE) down --remove-orphans

backend-local-logs:
	$(LOCAL_COMPOSE) logs -f api

db-migrate:
	$(COMPOSE) run --build --rm migrate .venv/bin/alembic upgrade head

db-migrate-check:
	$(COMPOSE) run --build --rm migrate

db-migrate-local:
	$(LOCAL_COMPOSE) up -d --wait postgres
	$(LOCAL_COMPOSE) run --build --rm migrate

db-seed:
	cd apps/api && uv run python -m scripts.seed_dev

db-seed-local: db-migrate-local
	$(LOCAL_COMPOSE) run --build --rm api .venv/bin/python -m scripts.seed_dev

db-migration-smoke:
	@status=0; \
	docker compose -f infra/docker-compose.migration-smoke.yml \
		up --build --abort-on-container-exit --exit-code-from migrate-smoke || status=$$?; \
	docker compose -f infra/docker-compose.migration-smoke.yml down --remove-orphans; \
	exit $$status

# ── DB 개편 리허설 ──────────────────────────────────────────────
# 프로덕션 덤프를 격리 DB(포트 5433)에 복원해두고 새 마이그레이션·배치를 미리 돌려본다.
# 프로덕션 덤프 획득은 자동화하지 않는다 — 사용자가 직접 떠온 파일을 DUMP= 로 넘긴다.

# dev DB(.env DATABASE_URL)에서 읽기 전용 덤프. 산출물은 infra/dumps/(gitignore).
db-dump-dev:
	infra/scripts/dump_dev_db.sh

# 리허설 Postgres 기동(로컬 개발 DB와 분리 — 컨테이너·포트·볼륨 별도).
db-rehearsal-up:
	$(REHEARSAL_COMPOSE) up -d --wait postgres-rehearsal

# 덤프 파일을 리허설 DB 에 복원 + alembic_version 검증. 예: make db-rehearsal-restore DUMP=infra/dumps/prod.dump
db-rehearsal-restore:
	infra/scripts/restore_rehearsal.sh $(DUMP)

# 복원본 위에서 새 마이그레이션을 리허설(alembic upgrade head).
db-rehearsal-migrate:
	$(REHEARSAL_COMPOSE) --profile migrate run --build --rm migrate-rehearsal

# 리허설 환경 정리(볼륨까지 삭제해 복원 데이터를 남기지 않는다).
db-rehearsal-down:
	$(REHEARSAL_COMPOSE) down --volumes --remove-orphans

# 규정·가이드 질문. 로컬 씨앗에 문서 15편·규정 12건이 다 있어 로컬로 충분하다.
chat-check:
	@mkdir -p tmp
	@$(LOCAL_COMPOSE) run --build --rm -T api .venv/bin/python -m scripts.chat_quality_check \
		--set rules $(if $(MODELS),--models $(MODELS)) $(if $(REPEAT),--repeat $(REPEAT)) \
		> tmp/chat-quality-rules.md
	@echo "→ tmp/chat-quality-rules.md"

# 검색이 필요 없는 질문(인사·제주 밖·의료·되묻기). 탈출구가 열리는지만 보므로
# 장소 데이터를 타지 않는다 — 로컬로 충분하다.
chat-check-guardrails:
	@mkdir -p tmp
	@$(LOCAL_COMPOSE) run --build --rm -T api .venv/bin/python -m scripts.chat_quality_check \
		--set guardrails $(if $(MODELS),--models $(MODELS)) $(if $(REPEAT),--repeat $(REPEAT)) \
		> tmp/chat-quality-guardrails.md
	@echo "→ tmp/chat-quality-guardrails.md"

# 장소 질문. **팀 RDS 로만 검증된다** — 로컬 씨앗 장소 4건은 region 이 챗봇 어휘
# 밖이라 어떤 지역 질문도 0건이다. 그래서 컨테이너가 아니라 .env 의 DATABASE_URL 로 붙는다.
chat-check-places:
	@mkdir -p tmp
	@cd apps/api && uv run python -m scripts.chat_quality_check \
		--set places $(if $(MODELS),--models $(MODELS)) $(if $(REPEAT),--repeat $(REPEAT)) \
		> ../../tmp/chat-quality-places.md
	@echo "→ tmp/chat-quality-places.md"

lint:
	cd apps/mobile && npm run lint
	cd apps/api && uv run ruff check .

typecheck:
	cd apps/mobile && npm run typecheck

test:
	cd apps/api && uv run pytest

check: lint typecheck test
