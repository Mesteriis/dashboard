# syntax=docker/dockerfile:1.7

ARG PYTHON_VERSION=3.14-slim
ARG NODE_VERSION=20-alpine

############################
# 1) Frontend build (Vite)
############################
FROM node:${NODE_VERSION} AS frontend_builder
WORKDIR /frontend

COPY src/frontend/package.json src/frontend/package-lock.json ./
RUN npm ci

COPY src/frontend/ ./
RUN npm run build

############################
# 2) Backend runtime
############################
FROM python:${PYTHON_VERSION} AS backend_runtime
WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

COPY src/main.py /app/src/main.py
COPY src/api/ /app/src/api/
COPY src/config/ /app/src/config/
COPY src/scheme/ /app/src/scheme/
COPY src/service/ /app/src/service/
COPY src/tools/ /app/src/tools/
COPY dashboard.yaml /app/dashboard.yaml
COPY src/templates/ /app/src/templates/
COPY src/static/ /app/src/static/

COPY --from=frontend_builder /frontend/dist/ /app/src/static/
COPY --from=frontend_builder /frontend/dist/index.html /app/src/templates/index.html

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    DASHBOARD_PORT=8090 \
    LAN_SCAN_ENABLED=false \
    LAN_SCAN_RUN_ON_STARTUP=false \
    DASHBOARD_HEALTHCHECK_VERIFY_TLS=true \
    LAN_SCAN_HTTP_VERIFY_TLS=true

EXPOSE 8090
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8090"]
