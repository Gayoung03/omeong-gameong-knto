FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev

COPY app ./app
COPY alembic.ini ./alembic.ini
COPY migrations ./migrations
# 운영 스크립트(시드 비번 패치·백필·중복 머지 등)를 이미지에 포함한다.
# 없으면 프로덕션(railway ssh)에서 `python -m scripts.*` 실행이 불가하다.
COPY scripts ./scripts

EXPOSE 8000

CMD [".venv/bin/fastapi", "run", "app/main.py", "--port", "8000"]
