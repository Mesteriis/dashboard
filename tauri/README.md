# Tauri Desktop Shell

`tauri/` — desktop-оболочка Oko для macOS Apple Silicon, которая упаковывает frontend и добавляет runtime-режимы подключения к backend (`remote` / `embedded`).

## Роль в продукте

Desktop-контур нужен для сценариев, где важны:
- единый локальный клиент без браузерной зависимости;
- быстрый переключатель между удалённым и встроенным backend;
- системная интеграция (tray, native menu, оконная модель).

Бизнес-ценность:
- снижает friction для ежедневного NOC/SRE использования;
- упрощает «single-app» дистрибуцию для локальных команд;
- даёт гибкую модель thin/thick клиента.

## Runtime profile model

В shell поддерживаются режимы:

- `remote`: UI работает с внешним backend (`remote_base_url`).
- `embedded`: shell поднимает локальный sidecar backend на свободном порту и направляет UI на него.

Frontend получает профиль через Tauri commands/events:
- command: `desktop_get_runtime_profile`
- command: `desktop_set_runtime_profile`
- event: `desktop://runtime-profile`
- event: `desktop://action`

## Архитектура desktop runtime

```text
Tauri Window/WebView
   |
   | invoke + events
   v
Rust runtime state (DesktopState)
   |
   | spawn/stop
   v
Embedded backend sidecar (optional)
   |
   v
HTTP API base URL for frontend (__OKO_API_BASE__)
```

Компоненты:
- `src/main.rs` — runtime orchestration, profile persistence, menu/tray, process lifecycle;
- `tauri.conf.json` — window/build/bundle конфигурация;
- `binaries/oko-backend-aarch64-apple-darwin` — embedded sidecar binary;
- `resources/dashboard.default.yaml` — стартовый шаблон конфигурации.

## Требования платформы

Текущая сборка ориентирована на:
- `macOS`
- `aarch64` (Apple Silicon)

В `main.rs` есть явная проверка архитектуры (`ensure_apple_silicon`).

## Локальная разработка

Из каталога `frontend/`:

```bash
npm run tauri:dev
```

Что происходит перед запуском:
1. `sync-default-config.mjs` копирует `dashboard.yaml` в `tauri/resources/dashboard.default.yaml`.
2. `ensure-sidecar.mjs` проверяет/собирает sidecar binary.
3. запускается `tauri dev`.

## Production build (ARM64)

```bash
cd frontend
npm run tauri:build:arm64
```

Или через helper-скрипт верхнего уровня:

```bash
./scripts/build_macos_app_arm64.sh
```

Итоговые артефакты:
- `.data/artifacts/macos-arm64/output/Oko.app`
- `.data/artifacts/macos-arm64/output/Oko.app.zip`

## Embedded sidecar pipeline

Sidecar собирается скриптом:

```bash
./scripts/build_sidecar_macos_arm64.sh
```

Скрипт:
- использует `pyinstaller` (через `uv` при наличии);
- собирает `scripts/backend_sidecar.py` в single binary;
- копирует бинарник в `tauri/binaries/oko-backend-aarch64-apple-darwin`.

## Runtime state и файловая модель

Desktop хранит профиль и runtime-данные локально:
- runtime profile: `desktop-runtime.json` (в app config dir)
- пользовательская runtime папка: `~/.oko`
- файлы в runtime:
  - `dashboard.yaml`
  - `data/dashboard.sqlite3` (если sidecar использует sqlite-профиль)
  - `logs/backend.log`
  - `backend.pid`

## Меню и tray

Shell поднимает native menu + tray с действиями:
- показать окно
- открыть поиск
- открыть настройки
- quit

Действия пробрасываются во frontend через `desktop://action`.

## Конфигурация

Ключевые места:
- `tauri/tauri.conf.json`
- `frontend/scripts/sync-default-config.mjs`
- `scripts/build_sidecar_macos_arm64.sh`
- `scripts/build_macos_app_arm64.sh`

Полезные переменные:
- `OKO_DESKTOP_BACKEND_BIN`
- `OKO_DESKTOP_DEFAULT_CONFIG`
- `OKO_DESKTOP_ARTIFACTS_DIR`
- `OKO_SIDECAR_*`

## Важные замечания по текущему состоянию

- Скрипт `sync-default-config.mjs` ожидает файл `dashboard.yaml` в корне репозитория.
  Если у вас только `_dashboard.yaml`, создайте копию/синк перед desktop сборкой.
- Embedded backend запускается как отдельный процесс и управляется PID-файлом, поэтому корректное завершение приложения важно для чистого lifecycle.

## OSS-модель развития desktop части

- Изменения runtime profile API должны быть синхронно обновлены в:
  - `tauri/src/main.rs`
  - `frontend/src/features/services/desktopRuntime.ts`
- Изменения process-management обязаны проходить ручную проверку сценариев:
  - switch `remote` -> `embedded`
  - restart приложения
  - восстановление после stale PID.
- Любые изменения build pipeline должны сопровождаться обновлением скриптов и документации в этом файле.
