# Backend (Oko Core API)

Backend — это server-side ядро платформы: API-контракт, жизненный цикл конфигурации, action execution, plugin runtime, health-мониторинг и интеграция с внутренней событийной шиной.

## Роль в продукте

Backend отвечает за два бизнес-критичных контура:
- **Контур управления**: конфигурация дашборда, реестры действий/виджетов, операции плагинов.
- **Контур наблюдаемости**: сбор health-сигналов, вычисление статусов, публикация событий в клиентские подписки.

Практический эффект:
- единый API для web и desktop клиентов;
- предсказуемое выполнение автоматизации через Action Gateway;
- деградации/падения сервисов быстро доходят до UI через SSE.

## Runtime topology

В коде заложены две роли процесса:

- `OKO_RUNTIME_ROLE=backend`
- `OKO_RUNTIME_ROLE=worker`

### `backend` роль

- Поднимает FastAPI (`backend/main.py`).
- Инициализирует контейнер зависимостей (`config/container.py`).
- Публикует события, запускает bootstrap конфигурации.
- Может работать с локальными consumer'ами (memory bus или `OKO_ENABLE_LOCAL_CONSUMERS=true`).

### `worker` роль

- Запускается через `python -m oko.worker`.
- Подписывается на bus очереди storage/actions/health.
- Выполняет фоновую обработку и периодический health scheduler.

## Архитектура слоёв

```text
API Layer
  - api/v1/core.py
  - api/v1/actions.py
  - api/v1/plugins.py
  - api/v1/store.py

Application Layer
  - core/config/ConfigService
  - core/gateway/ActionGateway
  - apps/health/* (scheduler/checkers/repository/status)
  - core/plugins/PluginService

Integration Layer
  - core/bus/* (RabbitMQ client + RPC)
  - core/events/* (publish/consume + SSE bridge)
  - core/plugins/store.py (StoreClient/PluginInstaller)

Persistence Layer
  - SQLAlchemy models/repositories
  - Postgres (primary production target)
  - Alembic migrations
  - Plugin storage (universal + physical table mode router)
```

## API surface (`/api/v1`)

### Core

- `GET /health`
- `GET /favicon`
- `GET /state`
- `GET /config`
- `POST /config/import`
- `POST /config/validate`
- `POST /config/patch`
- `POST /config/rollback`
- `GET /config/revisions`
- `GET /widgets/registry`
- `GET /events/stream`

### Actions

- `GET /actions/registry`
- `POST /actions/validate`
- `POST /actions/execute`
- `GET /actions/history`

### Plugins

- `GET /plugins`
- `GET /plugins/registry`
- `GET /plugins/{plugin_id}`
- `GET /plugins/{plugin_id}/manifest`
- `GET /plugins/{plugin_id}/services`
- `GET /plugins/{plugin_id}/settings`
- `PUT /plugins/{plugin_id}/settings`
- `POST /plugins/{plugin_id}/load`
- `POST /plugins/{plugin_id}/unload`
- `POST /plugins/{plugin_id}/reload`
- `POST /plugins/{plugin_id}/enable`
- `POST /plugins/{plugin_id}/disable`
- `DELETE /plugins/{plugin_id}`

### Store Integration

- `GET /store`
- `GET /store/health`
- `GET /store/{plugin_id}`
- `POST /store/{plugin_id}/install`
- `POST /store/{plugin_id}/uninstall`

## Security model (capability-based)

Каждый защищённый endpoint использует capability dependency (`core/security/deps.py`).

Требуемые заголовки:
- `X-Oko-Actor`
- `X-Oko-Capabilities`

Пример:

```bash
curl http://127.0.0.1:8000/api/v1/state \
  -H 'X-Oko-Actor: local-dev' \
  -H 'X-Oko-Capabilities: read.state,read.events'
```

## Event & bus model

### Внутренняя шина (RabbitMQ)

- Exchange: `oko.bus` (`topic`)
- Очереди:
  - `oko.bus.storage`
  - `oko.bus.actions`
  - `oko.bus.events`
  - `oko.bus.health.check.request`
  - `oko.bus.health.check.result`

### Основные routing keys

- `storage.kv.*`
- `storage.table.*`
- `action.execute`
- `event.publish`
- `health.check.request`
- `health.check.result`

### SSE bridge

Путь: `GET /api/v1/events/stream`

Поток:
1. backend подписывает клиента на `EventBus`;
2. отдаёт initial snapshot (`core.state.snapshot` + `health.state.snapshot`);
3. ретранслирует новые события из bus;
4. отправляет keepalive каждые `OKO_EVENTS_KEEPALIVE_SEC`.

## Health subsystem

Ключевые элементы:
- `HealthScheduler` — синхронизирует monitored services из активной конфигурации и планирует проверки;
- `HealthChecker` — выполняет HTTP/TCP/ICMP check;
- `HealthCheckResultConsumer` — принимает результаты и сохраняет window state;
- `evaluate_health` — определяет `online/degraded/down/unknown`.

Сигналы публикуются в event pipeline и попадают в UI через SSE.

## Plugin runtime

Папка установки: `backend/plugins/`.

Возможности runtime:
- scan/discover плагинов;
- load/unload/reload/enable/disable;
- динамический mount page/api routes;
- lifecycle hooks: `on_startup`, `on_shutdown`;
- watch loop (`OKO_PLUGIN_WATCH_POLL_SEC`) для hot refresh.

Интеграция со Store выполняется через `StoreClient` + `PluginInstaller`.

## Storage architecture

Backend поддерживает 2 storage-режима для плагинов:

- `core_universal` — универсальные таблицы (`plugin_rows`, `plugin_indexes`, `plugin_kv` и т.д.).
- `core_physical_tables` — физические таблицы per plugin/table на основе DDL-спеков.

Переключение и маршрутизация реализованы в `core/storage/router.py`.

## Запуск локально

### 1. Инфраструктура

```bash
docker compose -f docker-compose.deps.yml up -d
```

### 2. Backend API

```bash
export DATABASE_URL=postgresql+asyncpg://oko:oko@localhost:5432/oko
export BROKER_URL=amqp://oko:oko@localhost:5672/
export OKO_RUNTIME_ROLE=backend
export OKO_BOOTSTRAP_CONFIG_FILE=_dashboard.yaml
PYTHONPATH=backend uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Worker

```bash
export DATABASE_URL=postgresql+asyncpg://oko:oko@localhost:5432/oko
export BROKER_URL=amqp://oko:oko@localhost:5672/
export OKO_RUNTIME_ROLE=worker
PYTHONPATH=backend uv run python -m oko.worker
```

## Миграции

```bash
PYTHONPATH=backend uv run alembic -c alembic.ini upgrade head
```

## Тестирование

```bash
uv run pytest tests/backend
```

Интеграционный сценарий (Postgres + RabbitMQ + SSE bridge):

```bash
OKO_RUN_INTEGRATION=1 PYTHONPATH=backend uv run --group dev \
  pytest tests/backend/integration/test_compose_e2e.py --no-cov -m integration
```

## Ключевые переменные окружения

- `DATABASE_URL`
- `BROKER_URL`
- `OKO_RUNTIME_ROLE`
- `OKO_ENABLE_LOCAL_CONSUMERS`
- `OKO_BOOTSTRAP_CONFIG_FILE`
- `OKO_EVENTS_KEEPALIVE_SEC`
- `OKO_ACTIONS_EXECUTE_ENABLED`
- `OKO_STORAGE_RPC_TIMEOUT_SEC`
- `OKO_ACTION_RPC_TIMEOUT_SEC`
- `OKO_BROKER_PREFETCH_COUNT`
- `OKO_STORE_URL`
- `OKO_PLUGIN_WATCH_POLL_SEC`
- `OKO_HEALTH_*`
- `OKO_FAVICON_*`

## OSS-ready модель развития backend

- Любое изменение API должно сопровождаться тестом в `tests/backend/core`.
- Любое изменение bus/storage контрактов должно иметь покрытие unit + integration.
- Изменения в plugin lifecycle допускаются только с обратной совместимостью `manifest.py`/`ui.yaml`.
- Для production-изменений обязательно описывать impact на:
  - runtime роли (`backend`/`worker`);
  - storage migration;
  - события (`event.type`), потребляемые UI.
