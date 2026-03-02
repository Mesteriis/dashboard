# Frontend (Vue 3 SPA)

Frontend — клиентская оболочка Oko Dashboard, которая агрегирует конфигурацию, состояние инфраструктуры, plugin UI и runtime-переключения (web/desktop) в единый UX.

## Роль в продукте

Frontend даёт операционной команде единый рабочий контур:
- быстро переходить к сервисам и группам;
- видеть текущий health-срез инфраструктуры;
- выполнять действия через backend API;
- управлять плагинами и настройками runtime;
- работать как в браузере, так и внутри desktop shell.

Бизнес-эффект:
- меньше переключений между инструментами;
- более короткий путь от инцидента до действия;
- единый UX для разных каналов доставки (web/desktop).

## Технологический стек

- Vue 3 (`script setup` + composition API)
- Vue Router
- TypeScript
- Vite
- SCSS (система токенов и модулей стилей)
- Tauri bridge (`@tauri-apps/api`) для desktop runtime

## Архитектурная модель

UI организован по слоям (см. также `ARCHITECTURE_UI.md`):

1. `src/ui/` — атомарные контролы и базовые поверхности.
2. `src/components/` — переиспользуемые layout-блоки без доменной логики.
3. `src/primitives/` — абстрактные interaction-паттерны (tabs, tree, table, modal).
4. `src/views/` — доменные композиции (dashboard/plugins/settings/overlays).
5. `src/pages/` — route entry points.
6. `src/features/` — бизнес-логика: stores, API services, composables.
7. `src/shared/` — контракты, константы, утилиты.

Принцип: side effects и сеть живут в `features`, а UI-слои остаются максимально детерминированными.

## Routing карта

Маршруты (`src/router.ts`):
- `/` — dashboard
- `/settings` — настройки
- `/ui` — UI showcase
- `/plugins` — plugin control center
- `/plugins/:pluginId` — plugin details/runtime page
- `/blank` — blank layout demo

## Состояние и runtime потоки

### Dashboard store

Центральный store создаётся через `createDashboardStore` и отвечает за:
- загрузку/патч конфигурации;
- tree/group/item CRUD;
- command palette;
- health indicators и виджеты;
- синхронизацию UI состояния между маршрутами.

### API слой

`requestJson.ts` строит все запросы к backend и добавляет:
- `X-Oko-Actor`
- `X-Oko-Capabilities`

`resolveRequestUrl()` учитывает `window.__OKO_API_BASE__`, что критично для desktop runtime profiles.

### Event stream

SSE-клиент (`eventStream.ts`) подключается к `/api/v1/events/stream`, парсит `id/event/data` кадры и подаёт события в store.

## Desktop runtime integration

`desktopRuntime.ts` поддерживает три режима:
- `web` — обычный браузерный клиент;
- `remote` — desktop UI + внешний backend;
- `embedded` — desktop UI + локальный sidecar backend.

Frontend слушает desktop events:
- `desktop://runtime-profile`
- `desktop://action`

и обновляет `window.__OKO_API_BASE__` для прозрачного переключения API endpoint.

## Скрипты разработки и сборки

Основные `npm scripts`:

- `npm run dev` — Vite dev server (`:5173`)
- `npm run build:web` — только Vite build в `../dist`
- `npm run build` — build + sync артефактов в backend:
  - `templates/index.html`
  - `static/assets/*`
- `npm run build:desktop` — desktop build assets pipeline
- `npm run tauri:dev` — запуск desktop приложения в dev
- `npm run tauri:build:arm64` — production desktop build (Apple Silicon)
- `npm run lint`
- `npm run typecheck`
- `npm run test`

## Build contract

### Web target

`npm run build` — единственная поддержанная команда для web-release артефактов backend runtime.

### Desktop target

Перед desktop сборкой выполняется:
- синхронизация default config в `tauri/resources/dashboard.default.yaml`;
- проверка/сборка sidecar binary;
- перенос static assets для desktop bundle.

## Тестирование и quality gates

```bash
npm run lint
npm run typecheck
npm run test
```

Отдельные сценарии:
- `npm run test:ui-kit`
- `npm run test:ui-kit:coverage`

Frontend тесты живут в `../tests/frontend/*.test.mjs`.

## Контракт с backend

Ключевые API направления:
- конфигурация: `/api/v1/config*`
- actions: `/api/v1/actions/*`
- stream: `/api/v1/events/stream`
- plugins: `/api/v1/plugins*`
- store bridge: `/api/v1/store*`

Важно: UI предполагает capability-based API. Если backend не выдаёт нужные capabilities, frontend корректно покажет ошибку доступа.

## Ограничения и особенности

- Продвинутая логика сосредоточена в `createDashboardStore`; при рефакторинге сохраняйте разделение по `sections/*`.
- Изменения структуры route/page должны быть согласованы с desktop navigation bridge.
- Для desktop-пайплайна требуется sidecar backend binary (создаётся скриптами `scripts/build_sidecar_macos_arm64.sh`).

## OSS-модель для frontend

- Новые UI элементы размещаются по слоистой архитектуре, а не в random-компонентах.
- Любое изменение API-клиентов должно иметь unit tests для `requestJson`/services.
- Любое изменение store-контрактов должно сопровождаться тестом на соответствующий сценарий UX.
- Не допускается прямой сетевой вызов внутри `ui/`, `components/`, `primitives/`.
