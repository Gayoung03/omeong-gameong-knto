COMPOSE = docker compose --env-file .env -f infra/docker-compose.yml
LOCAL_COMPOSE = $(COMPOSE) -f infra/docker-compose.local.yml

.PHONY: setup dev dev-local mobile-install api-install mobile-dev api-dev backend-up \
	backend-down backend-logs backend-local-up backend-local-down backend-local-logs \
	db-migrate db-migrate-check db-migrate-local db-seed db-seed-local \
	db-migration-smoke chat-check chat-check-places lint typecheck test check

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

# 규정·가이드 질문. 로컬 씨앗에 문서 15편·규정 12건이 다 있어 로컬로 충분하다.
chat-check:
	@mkdir -p tmp
	@$(LOCAL_COMPOSE) run --build --rm -T api .venv/bin/python -m scripts.chat_quality_check \
		--set rules $(if $(MODELS),--models $(MODELS)) > tmp/chat-quality-rules.md
	@echo "→ tmp/chat-quality-rules.md"

# 장소 질문. **팀 RDS 로만 검증된다** — 로컬 씨앗 장소 4건은 region 이 챗봇 어휘
# 밖이라 어떤 지역 질문도 0건이다. 그래서 컨테이너가 아니라 .env 의 DATABASE_URL 로 붙는다.
chat-check-places:
	@mkdir -p tmp
	@cd apps/api && uv run python -m scripts.chat_quality_check \
		--set places $(if $(MODELS),--models $(MODELS)) > ../../tmp/chat-quality-places.md
	@echo "→ tmp/chat-quality-places.md"

lint:
	cd apps/mobile && npm run lint
	cd apps/api && uv run ruff check .

typecheck:
	cd apps/mobile && npm run typecheck

test:
	cd apps/api && uv run pytest

check: lint typecheck test
