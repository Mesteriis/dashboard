# Oko Core (Server-first async stack)

Oko backend now runs as:

- FastAPI (`/api/v1`)
- Async SQLAlchemy + `asyncpg` (Postgres only)
- RabbitMQ internal bus (`oko.bus`)
- Worker process for actions/storage/plugin background runtime
- SSE stream for clients (`/api/v1/events/stream`)

## Local backend

```bash
export DATABASE_URL=postgresql+asyncpg://oko:oko@localhost:5432/oko
export BROKER_URL=amqp://oko:oko@localhost:5672/
export OKO_RUNTIME_ROLE=backend
PYTHONPATH=backend uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

## Local worker

```bash
export DATABASE_URL=postgresql+asyncpg://oko:oko@localhost:5432/oko
export BROKER_URL=amqp://oko:oko@localhost:5672/
export OKO_RUNTIME_ROLE=worker
PYTHONPATH=backend uv run python -m oko.worker
```

## Local frontend (Vite)

```bash
cd frontend
npm ci
npm run dev
```

Frontend dev server runs on `http://127.0.0.1:5173` and proxies `/api` to backend `http://127.0.0.1:8000`.

## Docker

```bash
docker compose up --build
```

Services:

- `postgres`
- `rabbitmq` (management on `15672`)
- `backend`
- `worker`
- optional `migrate` profile: `docker compose --profile migrate up migrate`

Infra only (deps for local backend/worker run):

```bash
docker compose -f docker-compose.deps.yml up -d
```

## Required env vars

- `DATABASE_URL`
- `BROKER_URL`
- `OKO_BOOTSTRAP_CONFIG_FILE`
- `OKO_EVENTS_KEEPALIVE_SEC`
- `OKO_ACTIONS_EXECUTE_ENABLED`
- `OKO_STORAGE_RPC_TIMEOUT_SEC`
- `OKO_ACTION_RPC_TIMEOUT_SEC`

## PyCharm run configs

Predefined shared run configs are stored in `.run/`:

- `01 Infra Up (docker)` - starts local Postgres+RabbitMQ only
- `02 Backend API (local)` - starts FastAPI backend from local sources
- `02 Backend API (local all-in-one)` - starts backend and local broker consumers in one process
- `03 Worker (local)` - starts async worker from local sources
- `04 Frontend Dev (local)` - starts Vite frontend
- `05 Full Stack (docker)` - starts full docker stack
- `06 Full Stack Down (docker)` - stops docker stack

All configs call `scripts/dev/stack.py`. You can override env vars (for example ports/URLs) directly in PyCharm Run Configuration UI.
If you want backend to also run broker consumers without a separate worker in local mode, set `OKO_ENABLE_LOCAL_CONSUMERS=true`.

## Integration test (real Postgres + RabbitMQ via Compose)

The test uses real infra from `tests/backend/integration/docker-compose.deps.yaml`, then runs backend runtime and a dedicated storage consumer process and validates:

- storage RPC path (`storage.table.upsert` via `BusClient.call()` + consumer reply)
- storage persistence in Postgres (`plugin_rows`)
- SSE bridge path (`event.publish` -> backend stream)

Run:

```bash
OKO_RUN_INTEGRATION=1 PYTHONPATH=backend uv run --group dev pytest tests/backend/integration/test_compose_e2e.py --no-cov -m integration
```
