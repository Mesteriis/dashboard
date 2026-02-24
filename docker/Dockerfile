# syntax=docker/dockerfile:1.7

ARG PYTHON_VERSION=3.11-slim
ARG NODE_VERSION=20-alpine

############################
# 1) Frontend build (Vite)
############################
FROM node:${NODE_VERSION} AS frontend_builder
WORKDIR /frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build:web

############################
# 2) Backend runtime
############################
FROM python:${PYTHON_VERSION} AS backend_runtime
WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

COPY backend/ /app/backend/
COPY alembic.ini /app/alembic.ini
COPY backend/alembic/ /app/backend/alembic/
COPY _dashboard.yaml /app/_dashboard.yaml
COPY static/ /app/static/
COPY templates/error/ /app/templates/error/

COPY --from=frontend_builder /dist/assets/ /app/static/assets/
COPY --from=frontend_builder /dist/index.html /app/templates/index.html

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend \
    PATH=/app/.venv/bin:$PATH \
    OKO_RUNTIME_ROLE=backend \
    DATABASE_URL=postgresql+asyncpg://oko:oko@postgres:5432/oko \
    BROKER_URL=amqp://oko:oko@rabbitmq:5672/ \
    OKO_BOOTSTRAP_CONFIG_FILE=/app/_dashboard.yaml

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
