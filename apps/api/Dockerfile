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
# 여행기록 카드에 손글씨를 얹을 때 쓰는 폰트. 이미지 안에 없으면 합성이 두부(□)로
# 그려지거나 실패한다. 라이선스·출처는 assets/fonts/README.md 참고.
COPY assets ./assets

EXPOSE 8000

CMD [".venv/bin/fastapi", "run", "app/main.py", "--port", "8000"]
