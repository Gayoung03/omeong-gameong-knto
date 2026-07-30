FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev

COPY app ./app

EXPOSE 8000

CMD ["uv", "run", "fastapi", "run", "app/main.py", "--port", "8000"]
