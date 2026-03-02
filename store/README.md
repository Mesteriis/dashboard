# Store Service (Plugin Catalog)

`store/` — отдельный FastAPI сервис, который хранит каталог плагинов, принимает ZIP/GitHub источники и предоставляет backend'у RPC-интерфейс для синхронизации и установки.

## Роль в платформе

Store отделяет lifecycle плагинов от основного backend runtime:
- backend не обязан знать, откуда взялся плагин;
- команды могут вести централизованный каталог расширений;
- установка в runtime идёт через контролируемый API, а не через ручное копирование.

Бизнес-ценность:
- масштабируемое управление расширяемостью;
- меньше рисков «ручной рассинхронизации» между окружениями;
- удобный вход для plugin ecosystem.

## Архитектура

```text
Store API (FastAPI)
  - /api/v1/plugins/*  (catalog + upload)
  - /api/v1/rpc/*      (backend integration)
  - /api/v1/health

Services
  - PluginStorageService (catalog, validation, extraction)
  - GitHubService (repo metadata/download helpers)

Persistence
  - filesystem storage
  - plugins.json metadata registry
  - uploads/* extracted plugin sources
```

## Ключевые сценарии

### 1. ZIP upload

1. Клиент отправляет файл в `POST /api/v1/plugins/upload/zip`.
2. Store сохраняет архив во временную зону `uploads/{plugin_id}`.
3. Распаковывает, валидирует `manifest.py`.
4. Добавляет запись в `plugins.json`.

### 2. GitHub import

1. Клиент отправляет `repo_url` + `branch` (+ optional `subdirectory`).
2. Store скачивает ZIP архива ветки.
3. Распаковывает и валидирует структуру плагина.
4. Обновляет каталог.

### 3. Backend sync/install

1. Backend вызывает `GET /api/v1/rpc/plugins`.
2. Для установки вызывает `POST /api/v1/rpc/plugins/download`.
3. Полученный путь копируется backend-установщиком в `backend/plugins/{plugin_name}`.

## API контракт

### Системные endpoint'ы

- `GET /api/v1/health`
- `GET /api/v1/info`

### Catalog endpoint'ы

- `GET /api/v1/plugins`
- `GET /api/v1/plugins/{plugin_id}`
- `POST /api/v1/plugins/upload/zip`
- `POST /api/v1/plugins/upload/github`
- `DELETE /api/v1/plugins/{plugin_id}`
- `GET /api/v1/plugins/{plugin_id}/path`

### RPC endpoint'ы (для backend)

- `GET /api/v1/rpc/plugins`
- `POST /api/v1/rpc/plugins/download`
- `GET /api/v1/rpc/plugins/{plugin_id}/manifest`
- `GET /api/v1/rpc/health`

## Plugin package contract

Минимальная структура:

```text
my-plugin/
  __init__.py
  manifest.py
```

Опционально:

```text
my-plugin/
  ui.yaml
  page_manifest.yaml
  plugin_manifest.py
  ...
```

`manifest.py` должен содержать минимум:
- `PLUGIN_NAME`
- `PLUGIN_VERSION`

## Локальный запуск

```bash
uv sync
uv run uvicorn store.main:app --reload --host 0.0.0.0 --port 8001
```

Проверка:

```bash
curl http://127.0.0.1:8001/api/v1/health
```

Swagger:
- `http://127.0.0.1:8001/docs`
- `http://127.0.0.1:8001/redoc`

## Запуск в Docker

Сервис объявлен в `docker-compose.yml` как `store`:

```bash
docker compose up --build store
```

## Конфигурация

`store/core/config.py` определяет поля:
- `host`, `port`
- `debug`
- `storage_path`
- `max_plugin_size_mb`
- `github_token`
- CORS-параметры

### Важно про текущее состояние реализации

В текущем коде есть практические ограничения:

- Фактический storage path жёстко закреплён как `store/plugins` (`HARDCODED_STORAGE_PATH` в `services/storage.py`).
- `max_plugin_size_mb` и `api_key` сейчас не применяются как runtime enforcement в upload endpoint'ах.
- Валидация манифеста сделана lightweight-парсером и подходит для базового contract-check, но не для sandbox/security hardening.

Эти ограничения стоит учитывать для production-профиля.

## Интеграция с backend

Backend использует:
- `StoreClient` для `sync_plugins`, `download_plugin`, `health_check`;
- `PluginInstaller` для копирования плагина в `backend/plugins`.

В backend интеграция включается переменной:
- `OKO_STORE_URL` (пример: `http://store:8001/api/v1`)

## Наблюдаемость и логирование

Store использует `structlog`:
- `debug=true` -> human-readable console renderer;
- `debug=false` -> JSON logs.

На старте выводит:
- путь storage;
- число найденных плагинов;
- краткие записи по каждому обнаруженному plugin entry.

## Security considerations

Текущая версия закрывает базовые риски (проверка структуры и наличия манифеста), но для production желательно добавить:
- строгую валидацию размера загрузки;
- authn/authz для upload/delete endpoint'ов;
- antivirus/static scanning для загружаемых архивов;
- sandbox для парсинга/обработки plugin артефактов.

## OSS-модель развития Store

Рекомендуемые правила изменений:
- Любые изменения catalog/RPC схем должны сопровождаться контрактными тестами.
- Добавление новых источников (Git provider, artifact storage) делать через сервисный слой, не смешивая с API handlers.
- Изменения plugin validation должны быть backward-compatible к существующему plugin contract.
- Функции безопасности (лимиты, auth, scanning) развивать как first-class дорожку, а не в виде ad-hoc middleware.
