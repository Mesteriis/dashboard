# Oko Dashboard

Платформа для управления и наблюдения за инфраструктурой: единая панель сервисов, health-мониторинг, событийная шина, расширяемость через плагины и desktop-режим.

## Что это за продукт

`Oko Dashboard` решает практическую задачу: собрать в одном интерфейсе технический ландшафт (сервисы, узлы, ссылки, статус, действия) и сделать его управляемым как для web, так и для desktop-клиента.

Ключевые возможности:
- централизованная конфигурация дашборда с ревизиями;
- выполнение действий через Action Gateway и аудит;
- мониторинг доступности сервисов (HTTP/TCP/ICMP) с публикацией состояния в SSE;
- плагинная модель с динамической загрузкой и отдельным Plugin Store;
- desktop-shell на Tauri с режимами `remote` и `embedded`.

## Бизнес-ценность

- Сокращает MTTR: состояние сервисов и маршруты к ним в одном месте.
- Ускоряет операционные действия: одинаковый API/UX для ручных и автоматизированных сценариев.
- Снижает стоимость интеграций: плагины можно подключать без форка core-части.
- Поддерживает гибкую модель внедрения: браузер, docker-стек, desktop-клиент.

## Структура монорепозитория

| Часть | Назначение | README |
|---|---|---|
| `backend/` | FastAPI API, Action/Config/Health домены, plugin runtime, bus integration | [backend/README.md](backend/README.md) |
| `frontend/` | Vue 3 SPA, визуальный shell, dashboard state, SSE/API клиенты | [frontend/README.md](frontend/README.md) |
| `store/` | Сервис каталога плагинов (ZIP/GitHub ingest + RPC для backend) | [store/README.md](store/README.md) |
| `tauri/` | Desktop оболочка (macOS ARM64), runtime profile, embedded sidecar | [tauri/README.md](tauri/README.md) |

Дополнительно:
- `tests/` — backend/frontend/integration тесты.
- `docker/`, `docker-compose*.yml` — контейнеризация и окружения.
- `scripts/` — dev/build automation (включая desktop sidecar).

## Архитектура на уровне системы

```text
Frontend (Vue) / Tauri WebView
        |
        | HTTP + SSE (/api/v1/*)
        v
Backend API (FastAPI, role=backend)
        |
        | publish/call
        v
RabbitMQ (oko.bus exchange) <---- Worker (role=worker)
        |
        v
PostgreSQL (core state, health, actions, storage)

Backend <----HTTP/RPC----> Store Service (plugin catalog)
```

Базовые принципы:
- API versioning: `/api/v1`.
- Runtime roles: `backend` и `worker`.
- Event delivery: bus -> in-memory event bus -> SSE stream.
- Security: capability-based access через заголовки `X-Oko-*`.

## Быстрый старт (локальная разработка)

### 1. Зависимости

- Python `>=3.11`
- Node.js `20.x`
- `uv`
- Docker + Docker Compose

### 2. Подготовка окружения

```bash
cp .env.example .env
uv sync --group dev
cd frontend && npm ci && cd ..
```

### 3. Поднять только инфраструктуру

```bash
docker compose -f docker-compose.deps.yml up -d
```

### 4. Запустить backend

```bash
export DATABASE_URL=postgresql+asyncpg://oko:oko@localhost:5432/oko
export BROKER_URL=amqp://oko:oko@localhost:5672/
export OKO_RUNTIME_ROLE=backend
export OKO_BOOTSTRAP_CONFIG_FILE=_dashboard.yaml
PYTHONPATH=backend uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Запустить worker

```bash
export DATABASE_URL=postgresql+asyncpg://oko:oko@localhost:5432/oko
export BROKER_URL=amqp://oko:oko@localhost:5672/
export OKO_RUNTIME_ROLE=worker
PYTHONPATH=backend uv run python -m oko.worker
```

### 6. Запустить frontend

```bash
cd frontend
npm run dev
```

Frontend: `http://127.0.0.1:5173` (проксирует `/api` на `http://127.0.0.1:8000`).

## Быстрый старт (Docker full stack)

```bash
docker compose up --build
```

Сервисы:
- `postgres`
- `rabbitmq`
- `backend`
- `worker`
- `store`
- опционально `migrate` профиль

## Quality Gates и проверки

```bash
make lint target=all
make test target=all
```

Полезные команды:
- backend unit tests: `uv run pytest tests/backend`
- frontend tests: `cd frontend && npm run test`
- integration (real Postgres + RabbitMQ):

```bash
OKO_RUN_INTEGRATION=1 PYTHONPATH=backend uv run --group dev \
  pytest tests/backend/integration/test_compose_e2e.py --no-cov -m integration
```

CI workflow включает: Ruff, mypy, pytest, ESLint, typecheck, frontend tests, pre-commit.

## Конфигурация и безопасность

Критичные переменные runtime:
- `DATABASE_URL`
- `BROKER_URL`
- `OKO_RUNTIME_ROLE`
- `OKO_BOOTSTRAP_CONFIG_FILE`
- `OKO_STORE_URL` (если нужна интеграция со Store)

Для вызова защищённых endpoint API требуются заголовки:
- `X-Oko-Actor`
- `X-Oko-Capabilities`

## Open Source Operating Model

Модель проекта ориентирована на OSS-процесс с явными quality-гейтами.

- Изменения вносятся через PR с обязательным запуском линтеров и тестов.
- Контракты API и runtime-поведение фиксируются тестами в `tests/backend` и `tests/frontend`.
- Расширения реализуются через plugins вместо хардфорка core.
- Документация по модулям ведётся отдельно, чтобы архитектурные решения были локальны к bounded context.

Рекомендуемый процесс вклада:
1. Создать feature-ветку от `main`.
2. Реализовать изменение в одном bounded context.
3. Добавить/обновить тесты.
4. Прогнать `make lint target=all` и `make test target=all`.
5. Описать в PR влияние на API/данные/операционные сценарии.

## Навигация по модулям

- [Backend](backend/README.md)
- [Frontend](frontend/README.md)
- [Store](store/README.md)
- [Tauri Desktop](tauri/README.md)
