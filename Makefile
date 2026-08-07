.PHONY: setup dev mobile-install api-install mobile-dev api-dev db-up db-down db-logs db-migrate \
	lint typecheck test check

setup: mobile-install api-install

dev: db-up db-migrate
	@trap '$(MAKE) --no-print-directory -C "$(CURDIR)" db-down' EXIT; \
	cd apps/mobile && npx concurrently \
		--kill-others \
		--names MOBILE,API \
		--prefix-colors cyan,magenta \
		"npm run dev" \
		"cd ../api && uv run fastapi dev app/main.py"

mobile-install:
	cd apps/mobile && npm ci

api-install:
	cd apps/api && uv sync --frozen

mobile-dev:
	cd apps/mobile && npm run dev

api-dev:
	cd apps/api && uv run fastapi dev app/main.py

db-up:
	docker compose -f infra/docker-compose.yml up -d --wait postgres

db-migrate:
	cd apps/api && uv run alembic upgrade head

db-down:
	docker compose -f infra/docker-compose.yml down

db-logs:
	docker compose -f infra/docker-compose.yml logs -f postgres

lint:
	cd apps/mobile && npm run lint
	cd apps/api && uv run ruff check .

typecheck:
	cd apps/mobile && npm run typecheck

test:
	cd apps/api && uv run pytest

check: lint typecheck test
