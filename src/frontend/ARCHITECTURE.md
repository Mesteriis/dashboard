# Фронтенд-архитектура OKO Dashboard

## Обзор

Фронтенд OKO Dashboard построен на **Vue 3** с использованием **Composition API** и **Vite** для сборки. Приложение представляет собой SPA (Single Page Application) с динамической загрузкой конфигурации и real-time обновлением состояния здоровья сервисов.

---

## Технологический стек

| Компонент | Технология                     | Версия   |
| --------- | ------------------------------ | -------- |
| Фреймворк | Vue 3                          | ^3.5.0   |
| Сборщик   | Vite                           | ^5.4.8   |
| Язык      | TypeScript + JavaScript        | ^5.9.3   |
| Стили     | SCSS + CSS Variables           | -        |
| Иконки    | Lucide Vue Next + Simple Icons | ^0.575.0 |
| Анимации  | @vueuse/motion                 | ^3.0.3   |
| Desktop   | Tauri API                      | ^2.8.0   |

---

## Структура директорий

```
src/frontend/
├── src/
│   ├── components/          # Vue-компоненты
│   │   ├── main/           # Основные компоненты страниц
│   │   │   ├── HeroPageTabs.vue
│   │   │   ├── IndicatorTabPanel.vue
│   │   │   ├── LanHostsTable.vue
│   │   │   ├── LanPageView.vue
│   │   │   ├── LanScanPanel.vue
│   │   │   ├── ServiceGroupCard.vue
│   │   │   ├── ServiceItemCard.vue
│   │   │   ├── ServicesGroupsPanel.vue
│   │   │   ├── ServicesHeroPanel.vue
│   │   │   └── VirtualizedItemGrid.vue
│   │   ├── modals/         # Модальные окна
│   │   ├── primitives/     # Базовые UI-примитивы
│   │   └── sidebar/        # Компоненты боковой панели
│   ├── stores/             # Управление состоянием
│   │   ├── dashboard/      # Модули хранилища dashboard
│   │   │   ├── icons/      # Иконки и резолверы
│   │   │   ├── configTreeIds.js
│   │   │   ├── configTreeLayout.js
│   │   │   ├── configTreeMove.js
│   │   │   ├── configTreeUtils.js
│   │   │   └── urlUtils.js
│   │   └── dashboardStore.js  # Основное хранилище
│   ├── views/              # Страницы приложения
│   │   ├── DashboardMainView.vue
│   │   └── DashboardSidebarView.vue
│   ├── services/           # API-клиенты и утилиты
│   ├── styles/             # Глобальные стили
│   ├── App.vue             # Корневой компонент
│   ├── main.js             # Точка входа
│   └── styles.scss         # Глобальные SCSS-стили
├── public/                 # Статические ресурсы
├── scripts/                # Build-скрипты
└── src-tauri/              # Tauri desktop обёртка
```

---

## Архитектурные слои

### 1. **Presentation Layer (Components)**

Компоненты разделены по уровням абстракции:

#### Primitives (Базовые компоненты)

- `UiButton.vue` - Кнопки
- `UiInput.vue` - Поля ввода
- `UiModal.vue` - Модальные окна
- `UiCard.vue` - Карточки

#### Layout Components

- `HeroPageTabs.vue` - Вкладки страниц
- `DashboardSidebarView.vue` - Боковая панель
- `VirtualizedItemGrid.vue` - Виртуализированная сетка

#### Domain Components

- `ServiceGroupCard.vue` - Карточка группы сервисов
- `ServiceItemCard.vue` - Карточка сервиса
- `LanHostsTable.vue` - Таблица LAN-хостов
- `LanScanPanel.vue` - Панель сканирования LAN

### 2. **State Management Layer (Stores)**

Приложение использует **кастомное хранилище состояния** на основе Vue 3 Reactivity API.

#### `dashboardStore.js` - Центральное хранилище

**Состояние:**

```javascript
{
  // Конфигурация
  config: ref(null),           // Загруженная конфигурация
  loadingConfig: ref(true),    // Флаг загрузки
  configError: ref(''),        // Ошибка загрузки

  // Навигация
  activePageId: ref(''),       // Активная страница
  treeFilter: ref(''),         // Фильтр дерева
  siteFilter: ref('all'),      // Фильтр по сайтам

  // UI состояние
  editMode: ref(false),        // Режим редактирования
  sidebarView: ref('detailed'), // Вид боковой панели
  serviceCardView: ref('detailed'), // Вид карточек
  statsExpanded: ref(false),   // Развёрнутая статистика

  // Здоровье сервисов
  healthStates: reactive({}),  // Состояния здоровья

  // LAN сканирование
  lanScanState: ref(null),     // Результат сканирования
  lanScanLoading: ref(false),  // Флаг загрузки

  // Модальные окна
  iframeModal: reactive({...}),
  itemEditor: reactive({...}),
  settingsPanel: reactive({...})
}
```

**Computed свойства:**

- `pages` - Список страниц (включая LAN)
- `widgets` - Виджеты из конфигурации
- `groupById` - Индекс групп по ID
- `subgroupById` - Индекс подгрупп по ID
- `itemIpById` - Маппинг items → IP адреса
- `commandPaletteEntries` - Элементы командной палитры
- `activePage` - Текущая активная страница
- `treeGroups` - Группы для отображения в дереве
- `sidebarIndicators` - Индикаторы боковой панели

**Методы:**

- `loadConfig()` - Загрузка конфигурации
- `saveConfig()` - Сохранение конфигурации
- `refreshHealth()` - Обновление здоровья
- `startHealthStream()` - SSE стрим здоровья
- `triggerLanScan()` - Запуск сканирования LAN
- `selectNode()` - Выбор узла дерева
- `moveItem()` - Перемещение элементов
- `toggleEditMode()` - Переключение режима редактирования

### 3. **Data Layer (Services)**

#### `dashboardApi.js` - API клиент

```javascript
// Основные endpoints
- fetchDashboardConfig()     → GET /api/v1/dashboard/config
- updateDashboardConfig()    → PUT /api/v1/dashboard/config
- fetchDashboardHealth()     → GET /api/v1/dashboard/health
- fetchDashboardHealthStream() → GET /api/v1/dashboard/health/stream
- fetchIframeSource()        → GET /api/v1/dashboard/iframe/{id}/source
- proxyIframe()              → GET /api/v1/dashboard/proxy/iframe/{id}
- fetchLanScanState()        → GET /api/v1/dashboard/lan-scan/state
- triggerLanScan()           → POST /api/v1/dashboard/lan-scan/trigger
```

#### `particlesLoader.js` - Загрузка анимаций

Динамическая загрузка particles.js для фоновых эффектов.

---

## Flow состояний

### 1. **Загрузка приложения**

```
main.js
  ↓
App.vue (mounted)
  ↓
dashboardStore.loadConfig()
  ↓
GET /api/v1/dashboard/config
  ↓
Применение темы (applyTheme)
  ↓
Применение сетки (applyGrid)
  ↓
startHealthStream()
  ↓
SSE подключение /api/v1/dashboard/health/stream
  ↓
Обновление healthStates в реальном времени
```

### 2. **SSE Health Stream**

```javascript
function startHealthStream() {
  healthStream = createDashboardHealthStream();

  healthStream.onmessage = (event) => {
    const data = JSON.parse(event.data);

    // Обновление состояний здоровья
    for (const item of data.items) {
      healthStates[item.item_id] = {
        ok: item.ok,
        level: item.level,
        latency_ms: item.latency_ms,
        status_code: item.status_code,
        history: item.history,
      };
    }

    // Обновление агрегатов
    config.aggregates = data.aggregates;
  };

  // Reconnect при обрыве
  healthStream.onerror = () => {
    setTimeout(startHealthStream, HEALTH_STREAM_RECONNECT_MS);
  };
}
```

### 3. **Редактирование конфигурации**

```
Пользователь нажимает "Edit"
  ↓
toggleEditMode() → editMode.value = true
  ↓
Перетаскивание элементов (Drag & Drop)
  ↓
dragState.type = 'item' | 'subgroup' | 'group'
  ↓
moveItemToSubgroupEnd() / moveGroup()
  ↓
Изменение config.value.groups
  ↓
Пользователь нажимает "Save"
  ↓
saveConfig()
  ↓
PUT /api/v1/dashboard/config
  ↓
saveStatus.value = 'saving' → 'saved' | 'error'
```

### 4. **LAN Сканирование**

```
triggerLanScan()
  ↓
POST /api/v1/dashboard/lan-scan/trigger
  ↓
lanScanActionBusy.value = true
  ↓
Polling каждые LAN_SCAN_POLL_MS
  ↓
GET /api/v1/dashboard/lan-scan/state
  ↓
lanScanState.value = { running, result, ... }
  ↓
Если !running → lanScanActionBusy.value = false
```

---

## Компонентная иерархия

```
App.vue
├── DashboardMainView.vue
│   ├── ServicesHeroPanel.vue
│   │   └── HeroPageTabs.vue
│   ├── ServicesGroupsPanel.vue
│   │   └── ServiceGroupCard.vue
│   │       └── ServiceItemCard.vue
│   ├── IndicatorTabPanel.vue
│   │   └── [Widget Components]
│   └── LanPageView.vue
│       ├── LanScanPanel.vue
│       └── LanHostsTable.vue
└── DashboardSidebarView.vue
    ├── Sidebar Navigation
    ├── Tree Filter
    └── Status Indicators
```

---

## Система иконок

### 1. **Brand Icons** (`stores/dashboard/icons/brandIcons.js`)

Брендовые иконки сервисов (Simple Icons):

```javascript
BRAND_ICON_BY_KEY = {
  proxmox: proxmoxIcon,
  "home-assistant": homeAssistantIcon,
  docker: dockerIcon,
  // ...
};
```

### 2. **Keyword Icons** (`stores/dashboard/icons/keywordIcons.js`)

Иконки по ключевым словам:

```javascript
ICON_RULES = [
  { keywords: ["db", "database"], icon: "database" },
  { keywords: ["net", "network"], icon: "network" },
  // ...
];
```

### 3. **Semantic Resolver** (`stores/dashboard/icons/semanticResolver.js`)

Умное определение иконок:

```javascript
resolveItemIcon(item) → icon_key
resolveGroupIcon(group) → icon_key
resolvePageIcon(page) → icon_key
```

---

## Управление состоянием

### Реактивность

Vue 3 Composition API обеспечивает реактивность:

```javascript
// Ref для примитивов
const activePageId = ref("");

// Reactive для объектов
const settingsPanel = reactive({ open: false });

// Computed для производных значений
const activePage = computed(() =>
  pages.value.find((p) => p.id === activePageId.value),
);
```

### Персистентность

UI состояние сохраняется в localStorage:

```javascript
const UI_STATE_STORAGE_KEY = "oko:dashboard-ui-state:v1";

function savePersistedUiState() {
  localStorage.setItem(
    UI_STATE_STORAGE_KEY,
    JSON.stringify({
      serviceCardView: serviceCardView.value,
      serviceGroupingMode: serviceGroupingMode.value,
      sidebarView: sidebarView.value,
      activePageId: activePageId.value,
      expandedGroups: expandedGroups,
      // ...
    }),
  );
}
```

---

## Анимации и эффекты

### Particles.js

Фоновые частицы для визуальных эффектов:

```javascript
const SIDEBAR_PARTICLES_CONFIG = {
  particles: {
    number: { value: 88 },
    color: { value: "#6df6e2" },
    line_linked: {
      enable: true,
      distance: 120,
      color: "#2dd4bf",
    },
  },
};
```

### @vueuse/motion

Анимации компонентов:

```vue
<template>
  <div
    v-motion="{
      initial: { opacity: 0, y: 20 },
      enter: { opacity: 1, y: 0 },
    }"
  >
    Content
  </div>
</template>
```

---

## Desktop интеграция (Tauri)

### API вызовы

```javascript
import { invoke } from "@tauri-apps/api/core";

// Вызов Rust функций из backend sidecar
await invoke("start_backend");
await invoke("get_backend_port");
```

### Режимы работы

1. **Remote** (тонкий клиент) - подключение к внешнему backend
2. **Embedded** (толстый клиент) - встроенный sidecar процесс

---

## Сборка и деплой

### Команды

```bash
# Development
npm run dev

# Production build
npm run build

# Desktop development
npm run tauri:dev

# Desktop build (ARM64)
npm run tauri:build:arm64

# Type checking
npm run typecheck

# Linting
npm run lint

# Tests
npm test
```

### Переменные окружения

```bash
OKO_DEV=true              # Development mode
OKO_BUILD_TARGET=desktop  # Desktop build
OKO_DEV_BACKEND_URL=...   # Dev backend URL
```

---

## Расширение функциональности

### Добавление нового компонента

1. Создать файл в `components/main/` или `components/primitives/`
2. Экспортировать компонент
3. Импортировать в родительском компоненте

### Добавление нового виджета

1. Добавить тип виджета в `scheme/dashboard.py` (backend)
2. Создать компонент отображения в `components/main/`
3. Добавить обработку в `dashboardStore.js`

### Добавление API endpoint

1. Добавить функцию в `services/dashboardApi.js`
2. Вызвать из store метода
3. Обработать ответ и обновить состояние

---

## Производительность

### Оптимизации

1. **Виртуализация** - `VirtualizedItemGrid.vue` для больших списков
2. **Мемоизация** - `computed` для производных данных
3. **Ленивая загрузка** - particles.js загружается только при необходимости
4. **SSE вместо polling** - real-time обновления здоровья

### Кэширование

- Конфигурация кэшируется с ETag
- Health данные обновляются по SSE
- UI состояние персистентно в localStorage

---

## Тестирование

```bash
# Запуск тестов
npm test

# Тесты покрывают:
- dashboardApi.endpoints.test.mjs  # API endpoints
- dashboardApi.requestJson.test.mjs # JSON запросы
- main.test.mjs                     # Основные функции
- app.test.mjs                      # App компонент
```

---

## Ссылки

- [Vue 3 Documentation](https://vuejs.org/)
- [Vite Documentation](https://vitejs.dev/)
- [Tauri Documentation](https://tauri.app/)
- [Lucide Icons](https://lucide.dev/)
- [Simple Icons](https://simpleicons.org/)
