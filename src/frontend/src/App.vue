<template>
  <div class="shell">
    <img class="center-emblem" :src="EMBLEM_SRC" alt="" aria-hidden="true" />

    <div class="app-shell">
      <aside class="sidebar">
        <div id="sidebar-particles" class="sidebar-particles" aria-hidden="true"></div>
        <div class="sidebar-content">
          <div class="brand">
            <img :src="EMBLEM_SRC" alt="Oko" />
            <div>
              <p class="brand-title">{{ appTitle }}</p>
              <p class="brand-subtitle">{{ appTagline }}</p>
            </div>
          </div>

          <nav class="tab-list" role="tablist" aria-label="Разделы">
            <button
              v-for="page in pages"
              :key="page.id"
              class="tab-btn"
              :class="{ active: activePage?.id === page.id }"
              type="button"
              role="tab"
              :title="page.title"
              :aria-label="page.title"
              :aria-selected="activePage?.id === page.id"
              @click="activePageId = page.id"
            >
              <component :is="resolvePageIcon(page)" class="ui-icon tab-tile-icon" />
              <span class="tab-tile-label">{{ page.title }}</span>
            </button>
          </nav>

          <section v-if="treeGroups.length" class="sidebar-tree" aria-label="Дерево сервисов">
            <div class="tree-topline">
              <p class="sidebar-tree-title">Навигация</p>
              <span class="tree-page-chip">{{ activePage?.title }}</span>
            </div>

            <label class="tree-search">
              <input
                v-model="treeFilter"
                type="search"
                placeholder="Поиск сервиса..."
                autocomplete="off"
                spellcheck="false"
              />
            </label>

            <div class="tree-root-page">
              <div class="tree-root-main">
                <component :is="resolvePageIcon(activePage)" class="ui-icon root-icon" />
                <div>
                <p class="tree-root-title">{{ activePage?.title }}</p>
                <p class="tree-root-subtitle">{{ activePage?.id }}</p>
                </div>
              </div>
              <span class="tree-root-meta">{{ pageHealthSummary.online }}/{{ pageHealthSummary.total }}</span>
            </div>

            <ul v-if="filteredTreeGroups.length" class="tree-root">
              <li v-for="group in filteredTreeGroups" :key="group.key" class="tree-group-item">
                <button
                  class="tree-node tree-group"
                  :class="{ active: isGroupSelected(group.key) }"
                  type="button"
                  @click="toggleGroupNode(group.key)"
                >
                  <span class="tree-caret" :class="{ open: isGroupExpanded(group.key) }">▾</span>
                  <component :is="resolveGroupIcon(group)" class="ui-icon tree-icon" />
                  <span class="tree-text">{{ group.title }}</span>
                  <span class="tree-meta">{{ groupOnlineItems(group) }}/{{ groupTotalItems(group) }}</span>
                </button>

                <ul v-show="isGroupExpanded(group.key)" class="tree-subgroups">
                  <li v-for="subgroup in group.subgroups" :key="subgroup.id" class="tree-subgroup-item">
                    <button
                      class="tree-node tree-subgroup"
                      :class="{ active: isSubgroupSelected(group.key, subgroup.id) }"
                      type="button"
                      @click="selectSubgroupNode(group.key, subgroup.id)"
                    >
                      <component :is="resolveSubgroupIcon(subgroup)" class="ui-icon tree-icon tree-sub-icon" />
                      <span class="tree-text">{{ subgroup.title }}</span>
                    </button>

                    <ul class="tree-items">
                      <li v-for="item in subgroup.items" :key="item.id" class="tree-item-row">
                        <button
                          class="tree-node tree-item"
                          :class="{ active: isItemSelected(item.id) }"
                          type="button"
                          @click="selectItemNode(group.key, subgroup.id, item.id)"
                        >
                          <span class="health-dot" :class="healthClass(item.id)"></span>
                          <component :is="resolveItemIcon(item)" class="ui-icon tree-icon tree-item-icon" />
                          <span class="tree-text">{{ item.title }}</span>
                        </button>
                      </li>
                    </ul>
                  </li>
                </ul>
              </li>
            </ul>

            <p v-else class="tree-empty">По вашему запросу ничего не найдено.</p>
          </section>

          <div class="sidebar-stats-accordion" aria-label="Индикаторы">
            <button
              class="sidebar-stats-toggle"
              type="button"
              aria-controls="sidebar-stats-panel"
              :aria-expanded="statsExpanded"
              @click="statsExpanded = !statsExpanded"
            >
              <span class="sidebar-stats-toggle-text">Индикаторы</span>
              <span class="sidebar-stats-toggle-values">{{ sidebarIndicatorSummary }}</span>
              <span class="sidebar-stats-toggle-caret" :class="{ open: statsExpanded }">▴</span>
            </button>

            <div id="sidebar-stats-panel" class="sidebar-stats-panel" :class="{ open: statsExpanded }">
              <div v-if="sidebarIndicators.length" class="sidebar-indicators">
                <article
                  v-for="widget in sidebarIndicators"
                  :key="widget.id"
                  class="sidebar-indicator"
                  :class="{
                    interactive: isLargeIndicator(widget),
                    active: activeIndicatorWidget?.id === widget.id,
                  }"
                  @click="selectSidebarIndicator(widget)"
                >
                  <header class="widget-head sidebar-indicator-head">
                    <div class="widget-title">
                      <component :is="resolveWidgetIcon(widget)" class="ui-icon widget-icon" />
                      <h3>{{ widget.title }}</h3>
                    </div>
                    <span class="item-type">{{ widget.type }}</span>
                  </header>

                  <p v-if="widgetState(widget.id)?.error" class="widget-error">{{ widgetState(widget.id)?.error }}</p>
                  <p v-else-if="widgetState(widget.id)?.loading" class="widget-loading">Обновление...</p>

                  <template v-else-if="widget.type === 'stat_card'">
                    <p class="widget-value sidebar-indicator-value">{{ statCardValue(widget) }}</p>
                    <p class="widget-subtitle">{{ statCardSubtitle(widget) }}</p>
                    <p v-if="statCardTrend(widget)" class="widget-trend">{{ statCardTrend(widget) }}</p>
                  </template>

                  <template v-else-if="widget.type === 'stat_list'">
                    <ul v-if="indicatorPreviewEntries(widget).length" class="widget-list sidebar-list-preview">
                      <li v-for="entry in indicatorPreviewEntries(widget)" :key="entry.title + entry.value">
                        <span>{{ entry.title }}</span>
                        <strong>{{ entry.value }}</strong>
                      </li>
                    </ul>
                    <p v-else class="widget-empty">Нет данных</p>
                    <p class="sidebar-indicator-hint">Нажмите, чтобы открыть во вкладке</p>
                  </template>

                  <template v-else-if="widget.type === 'table'">
                    <p class="widget-subtitle">Строк: {{ tableRows(widget).length }}</p>
                    <p class="sidebar-indicator-hint">Нажмите, чтобы открыть во вкладке</p>
                  </template>

                  <p v-else class="widget-empty">Неподдерживаемый тип виджета</p>

                  <div v-if="widget.data.actions?.length || isLargeIndicator(widget)" class="widget-actions sidebar-indicator-actions">
                    <button
                      v-if="isLargeIndicator(widget)"
                      class="ghost"
                      type="button"
                      @click.stop="openIndicatorView(widget.id)"
                    >
                      Открыть вкладку
                    </button>
                    <button
                      v-for="action in widget.data.actions || []"
                      :key="action.id"
                      class="ghost"
                      type="button"
                      :disabled="isActionBusy(widget.id, action.id)"
                      @click.stop="runWidgetAction(widget.id, action)"
                    >
                      {{ action.title }}
                    </button>
                  </div>
                </article>
              </div>
              <p v-else class="widget-empty">Для выбранной страницы индикаторы не настроены.</p>
            </div>
          </div>
        </div>
      </aside>

      <main :key="activePage?.id || 'empty'" class="page" :class="{ 'indicator-open': Boolean(activeIndicatorWidget) }">
        <section v-if="loadingConfig" class="panel status-panel">
          <h2>Загрузка конфигурации...</h2>
          <p class="subtitle">Получаем dashboard-модель из backend.</p>
        </section>

        <section v-else-if="configError" class="panel status-panel error-state">
          <h2>Ошибка загрузки конфигурации</h2>
          <p class="subtitle">{{ configError }}</p>
          <button class="ghost" type="button" @click="loadConfig">Повторить</button>
        </section>

        <template v-else-if="activePage">
          <section v-if="activeIndicatorWidget" class="panel indicator-tab-panel">
            <header class="indicator-tab-head">
              <div class="indicator-tab-title">
                <component :is="resolveWidgetIcon(activeIndicatorWidget)" class="ui-icon widget-icon" />
                <h2>{{ activeIndicatorWidget.title }}</h2>
              </div>
              <div class="indicator-tab-controls">
                <span class="item-type">{{ activeIndicatorWidget.type }}</span>
                <button class="ghost" type="button" @click="refreshWidget(activeIndicatorWidget.id)">Обновить</button>
                <button class="ghost" type="button" @click="activeIndicatorViewId = ''">Закрыть вкладку</button>
              </div>
            </header>

            <div class="indicator-tab-content">
              <p v-if="widgetState(activeIndicatorWidget.id)?.error" class="widget-error">
                {{ widgetState(activeIndicatorWidget.id)?.error }}
              </p>
              <p v-else-if="widgetState(activeIndicatorWidget.id)?.loading" class="widget-loading">Обновление...</p>

              <template v-else-if="activeIndicatorWidget.type === 'stat_list'">
                <ul v-if="statListEntries(activeIndicatorWidget).length" class="widget-list">
                  <li v-for="entry in statListEntries(activeIndicatorWidget)" :key="entry.title + entry.value">
                    <span>{{ entry.title }}</span>
                    <strong>{{ entry.value }}</strong>
                  </li>
                </ul>
                <p v-else class="widget-empty">Нет данных</p>
              </template>

              <template v-else-if="activeIndicatorWidget.type === 'table'">
                <div v-if="tableRows(activeIndicatorWidget).length" class="widget-table-wrap">
                  <table class="widget-table">
                    <thead>
                      <tr>
                        <th v-for="column in activeIndicatorWidget.data.columns" :key="column.key">{{ column.title }}</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(row, rowIndex) in tableRows(activeIndicatorWidget)" :key="rowIndex">
                        <td v-for="column in activeIndicatorWidget.data.columns" :key="column.key">{{ row?.[column.key] ?? '-' }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <p v-else class="widget-empty">Нет данных</p>
              </template>
            </div>

            <div v-if="activeIndicatorWidget.data.actions?.length" class="widget-actions">
              <button
                v-for="action in activeIndicatorWidget.data.actions"
                :key="action.id"
                class="ghost"
                type="button"
                :disabled="isActionBusy(activeIndicatorWidget.id, action.id)"
                @click="runWidgetAction(activeIndicatorWidget.id, action)"
              >
                {{ action.title }}
              </button>
            </div>
          </section>

          <template v-else>
            <header class="hero panel">
              <p class="eyebrow">{{ activePage.id }}</p>
              <h1>{{ activePage.title }}</h1>
              <p class="subtitle">{{ appTagline }}</p>
            </header>

            <section class="page-stack">
              <section
                v-for="(block, index) in activePageGroupBlocks"
                :key="`${activePage.id}:${index}:groups`"
                class="block-wrap"
              >
                <section class="groups-grid">
                  <article
                    v-for="group in filteredBlockGroups(block.group_ids)"
                    :key="group.key"
                    class="panel group-panel"
                  >
                    <header class="group-header">
                      <div class="group-title-row">
                        <component :is="resolveGroupIcon(group)" class="ui-icon group-icon" />
                        <h2>{{ group.title }}</h2>
                      </div>
                      <p v-if="group.description" class="subtitle">{{ group.description }}</p>
                    </header>

                    <section v-for="subgroup in group.subgroups" :key="subgroup.id" class="subgroup">
                      <h3 class="subgroup-title">
                        <component :is="resolveSubgroupIcon(subgroup)" class="ui-icon subgroup-icon" />
                        <span>{{ subgroup.title }}</span>
                      </h3>
                      <div class="item-grid">
                        <article
                          v-for="item in subgroup.items"
                          :key="item.id"
                          class="item-card"
                          :class="{ selected: isItemSelected(item.id) }"
                        >
                          <div class="item-head">
                            <div class="item-title-row">
                              <component :is="resolveItemIcon(item)" class="ui-icon item-icon" />
                              <h4>{{ item.title }}</h4>
                            </div>
                            <span class="item-type">{{ item.type }}</span>
                          </div>

                          <p class="item-url">{{ item.url }}</p>

                          <div class="item-health">
                            <span class="health-dot" :class="healthClass(item.id)"></span>
                            <span class="health-text">{{ healthLabel(item.id) }}</span>
                          </div>

                          <div v-if="item.tags?.length" class="item-tags">
                            <span v-for="tag in item.tags" :key="tag" class="tag-pill">{{ tag }}</span>
                          </div>

                          <div class="item-actions">
                            <button class="ghost" type="button" @click="openItem(item)">
                              {{ item.type === 'iframe' ? 'Открыть iframe' : 'Открыть' }}
                            </button>
                            <button class="ghost" type="button" @click="copyUrl(item.url)">Копировать URL</button>
                          </div>
                        </article>
                      </div>
                    </section>
                  </article>

                  <article
                    v-if="!filteredBlockGroups(block.group_ids).length"
                    class="panel group-panel group-empty"
                  >
                    <h2>Нет данных для выбранного узла</h2>
                    <p class="subtitle">Выберите другую ветку в боковом дереве.</p>
                  </article>
                </section>
              </section>

              <article
                v-if="!activePageGroupBlocks.length"
                class="panel group-panel group-empty"
              >
                <h2>Для этой страницы нет групп</h2>
                <p class="subtitle">Откройте нужный индикатор в аккордеоне слева.</p>
              </article>
            </section>
          </template>
        </template>

        <section v-else class="panel status-panel">
          <h2>Нет доступных страниц</h2>
          <p class="subtitle">Проверьте `layout.pages` в `dashboard.yaml`.</p>
        </section>
      </main>
    </div>

    <div v-if="iframeModal.open" class="iframe-modal-backdrop" @click.self="closeIframeModal">
      <div class="iframe-modal">
        <header class="iframe-modal-header">
          <h3>{{ iframeModal.title }}</h3>
          <button class="ghost" type="button" @click="closeIframeModal">Закрыть</button>
        </header>

        <p v-if="iframeModal.loading" class="subtitle iframe-modal-status">Подготовка iframe...</p>
        <p v-else-if="iframeModal.error" class="widget-error iframe-modal-status">{{ iframeModal.error }}</p>
        <iframe
          v-else
          class="iframe-view"
          :src="iframeModal.src"
          :allow="iframeModal.allow || undefined"
          :sandbox="iframeModal.sandbox ? '' : undefined"
          :referrerpolicy="iframeModal.referrerPolicy || undefined"
        ></iframe>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, h, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import {
  Activity,
  Camera,
  ChartColumn,
  Circle,
  Cloud,
  Cpu,
  Database,
  Eye,
  Film,
  Folder,
  FolderTree,
  Gauge,
  GitBranch,
  Globe,
  HardDrive,
  HeartPulse,
  House,
  KeyRound,
  Layers,
  LayoutDashboard,
  Link2,
  Lock,
  Monitor,
  MonitorSmartphone,
  Music,
  Network,
  Package,
  Radar,
  Route,
  Server,
  Settings,
  Shield,
  Sparkles,
  Terminal,
  TriangleAlert,
  Tv,
  Wifi,
  Workflow,
  Wrench,
  Boxes,
} from 'lucide-vue-next'
import {
  siAdguard,
  siCockpit,
  siDocker,
  siGitea,
  siGrafana,
  siHomeassistant,
  siJellyfin,
  siNginx,
  siNginxproxymanager,
  siNpm,
  siOpenaigym,
  siOpenwrt,
  siPostgresql,
  siPortainer,
  siProxmox,
  siQbittorrent,
  siRadarr,
  siSonarr,
  siTermius,
  siYoutube,
  siYoutubeshorts,
} from 'simple-icons'
import { fetchDashboardConfig, fetchDashboardHealth, fetchIframeSource, requestJson } from './services/dashboardApi.js'

const EMBLEM_SRC = '/static/img/emblem-mark.png'
const HEALTH_REFRESH_MS = 30000
const LARGE_INDICATOR_TYPES = new Set(['stat_list', 'table'])

function createBrandIcon(icon) {
  const brandColor = `#${icon.hex}`
  return (_props, { attrs }) =>
    h(
      'svg',
      {
        ...attrs,
        xmlns: 'http://www.w3.org/2000/svg',
        viewBox: '0 0 24 24',
        fill: 'currentColor',
        role: 'img',
        'aria-hidden': 'true',
        style: attrs.style ? [attrs.style, { color: brandColor }] : { color: brandColor },
      },
      [h('path', { d: icon.path })]
    )
}

const BRAND_ICON_BY_KEY = {
  homeassistant: createBrandIcon(siHomeassistant),
  'home-assistant': createBrandIcon(siHomeassistant),
  ha: createBrandIcon(siHomeassistant),
  openwrt: createBrandIcon(siOpenwrt),
  adguard: createBrandIcon(siAdguard),
  proxmox: createBrandIcon(siProxmox),
  pve: createBrandIcon(siProxmox),
  grafana: createBrandIcon(siGrafana),
  gitea: createBrandIcon(siGitea),
  jellyfin: createBrandIcon(siJellyfin),
  jellyseerr: createBrandIcon(siJellyfin),
  sonarr: createBrandIcon(siSonarr),
  radarr: createBrandIcon(siRadarr),
  lidarr: createBrandIcon(siSonarr),
  readarr: createBrandIcon(siSonarr),
  bazarr: createBrandIcon(siSonarr),
  prowlarr: createBrandIcon(siSonarr),
  qbittorrent: createBrandIcon(siQbittorrent),
  qb: createBrandIcon(siQbittorrent),
  postgres: createBrandIcon(siPostgresql),
  postgresql: createBrandIcon(siPostgresql),
  docker: createBrandIcon(siDocker),
  dockge: createBrandIcon(siDocker),
  cockpit: createBrandIcon(siCockpit),
  npm: createBrandIcon(siNginxproxymanager),
  nginxproxymanager: createBrandIcon(siNginxproxymanager),
  'nginx-proxy-manager': createBrandIcon(siNginxproxymanager),
  nginx: createBrandIcon(siNginx),
  openai: createBrandIcon(siOpenaigym),
  ai: createBrandIcon(siOpenaigym),
  portainer: createBrandIcon(siPortainer),
  ytsync: createBrandIcon(siYoutubeshorts),
  youtube: createBrandIcon(siYoutube),
  youtubeshorts: createBrandIcon(siYoutubeshorts),
  termius: createBrandIcon(siTermius),
  termix: createBrandIcon(siTermius),
}

const ICON_BY_KEY = {
  home: House,
  house: House,
  дом: House,
  dom: House,
  route: Route,
  net: Network,
  network: Network,
  сеть: Network,
  dashboard: LayoutDashboard,
  infra: Server,
  infrastructure: Server,
  инфраструктура: Server,
  server: Server,
  core: Boxes,
  ops: Wrench,
  media: Tv,
  медиа: Tv,
  tv: Tv,
  iot: Cpu,
  cloud: Cloud,
  wifi: Wifi,
  monitor: Monitor,
  cockpit: MonitorSmartphone,
  proxmox: Server,
  grafana: ChartColumn,
  gitea: GitBranch,
  git: GitBranch,
  jellyfin: Film,
  navidrome: Music,
  tunnel: Radar,
  tunnels: Radar,
  stats: Gauge,
  services: Layers,
  service: Layers,
  health: HeartPulse,
  alerts: TriangleAlert,
  alert: TriangleAlert,
  security: Shield,
  auth: Lock,
  key: KeyRound,
  db: Database,
  database: Database,
  storage: HardDrive,
  link: Link2,
  iframe: Globe,
  terminal: Terminal,
  package: Package,
  music: Music,
  camera: Camera,
  eye: Eye,
  observability: Activity,
  workflow: Workflow,
  settings: Settings,
  spark: Sparkles,
}

const ICON_RULES = [
  { re: /\b(home|house|dom|дом)\b/, icon: House },
  { re: /\b(net|network|route|vpn|edge|сеть|маршрут|туннел)\b/, icon: Network },
  { re: /\b(infra|server|cluster|pve|проксмокс|инфраструктур)\b/, icon: Server },
  { re: /\b(media|tv|video|stream|jellyfin|медиа)\b/, icon: Film },
  { re: /\b(iot|sensor|home-assistant|умн|дом)\b/, icon: Cpu },
  { re: /\b(stat|metric|chart|grafana|аналит|monitor)\b/, icon: ChartColumn },
  { re: /\b(alert|error|warn|critical|ошиб|авар)\b/, icon: TriangleAlert },
  { re: /\b(health|status|pulse|heart|состояни)\b/, icon: HeartPulse },
  { re: /\b(auth|token|secret|lock|ключ|безопас)\b/, icon: Shield },
  { re: /\b(db|database|postgres|mysql|redis)\b/, icon: Database },
]

function normalizeIconToken(value) {
  return String(value || '')
    .toLowerCase()
    .replace(/[^a-z0-9а-яё._-]+/gi, ' ')
    .split(/[\\s._-]+/)
    .filter(Boolean)
}

function fromToken(token) {
  if (BRAND_ICON_BY_KEY[token]) return BRAND_ICON_BY_KEY[token]
  for (const [key, icon] of Object.entries(BRAND_ICON_BY_KEY)) {
    if (token.includes(key)) return icon
  }

  if (ICON_BY_KEY[token]) return ICON_BY_KEY[token]
  for (const [key, icon] of Object.entries(ICON_BY_KEY)) {
    if (token.includes(key)) return icon
  }
  return null
}

function pickSemanticIcon(sources, fallback) {
  for (const source of sources) {
    for (const token of normalizeIconToken(source)) {
      const icon = fromToken(token)
      if (icon) return icon
    }
  }

  const fullText = sources
    .map((source) => String(source || '').toLowerCase())
    .filter(Boolean)
    .join(' ')

  for (const rule of ICON_RULES) {
    if (rule.re.test(fullText)) return rule.icon
  }

  return fallback
}

const config = ref(null)
const loadingConfig = ref(true)
const configError = ref('')
const activePageId = ref('')
const treeFilter = ref('')
const statsExpanded = ref(false)
const activeIndicatorViewId = ref('')

const widgetStates = reactive({})
const actionBusy = reactive({})
const widgetIntervals = new Map()
let healthPollTimer = 0

const selectedNode = reactive({
  groupKey: '',
  subgroupId: '',
  itemId: '',
})

const expandedGroups = reactive({})
const healthStates = reactive({})

const iframeModal = reactive({
  open: false,
  title: '',
  src: '',
  allow: '',
  sandbox: false,
  referrerPolicy: '',
  loading: false,
  error: '',
})

const pages = computed(() => config.value?.layout?.pages || [])
const widgets = computed(() => config.value?.widgets || [])

const appTitle = computed(() => config.value?.app?.title || 'Oko')
const appTagline = computed(() => config.value?.app?.tagline || 'Your Infrastructure in Sight')

const widgetById = computed(() => {
  const map = new Map()
  for (const widget of widgets.value) {
    map.set(widget.id, widget)
  }
  return map
})

const groupById = computed(() => {
  const map = new Map()
  for (const group of config.value?.groups || []) {
    map.set(group.id, group)
  }
  return map
})

const subgroupById = computed(() => {
  const map = new Map()
  for (const group of config.value?.groups || []) {
    for (const subgroup of group.subgroups || []) {
      map.set(subgroup.id, { group, subgroup })
    }
  }
  return map
})

const activePage = computed(() => pages.value.find((page) => page.id === activePageId.value) || pages.value[0] || null)

const treeGroups = computed(() => {
  if (!activePage.value) return []

  const groupIds = []
  for (const block of activePage.value.blocks || []) {
    if (block?.type === 'groups') {
      groupIds.push(...(block.group_ids || []))
    }
  }

  return resolveBlockGroups(groupIds)
})

const filteredTreeGroups = computed(() => {
  const query = treeFilter.value.trim().toLowerCase()
  if (!query) return treeGroups.value

  return treeGroups.value
    .map((group) => {
      const groupMatches =
        String(group.title || '').toLowerCase().includes(query) ||
        String(group.description || '').toLowerCase().includes(query)

      if (groupMatches) {
        return {
          ...group,
          subgroups: group.subgroups || [],
        }
      }

      const matchedSubgroups = (group.subgroups || [])
        .map((subgroup) => {
          const subgroupMatches = String(subgroup.title || '').toLowerCase().includes(query)
          if (subgroupMatches) {
            return {
              ...subgroup,
              items: subgroup.items || [],
            }
          }

          const matchedItems = (subgroup.items || []).filter((item) => {
            const inTitle = String(item.title || '').toLowerCase().includes(query)
            const inUrl = String(item.url || '').toLowerCase().includes(query)
            const inTags = (item.tags || []).some((tag) => String(tag).toLowerCase().includes(query))
            return inTitle || inUrl || inTags
          })

          if (!matchedItems.length) return null
          return {
            ...subgroup,
            items: matchedItems,
          }
        })
        .filter(Boolean)

      if (!matchedSubgroups.length) return null
      return {
        ...group,
        subgroups: matchedSubgroups,
      }
    })
    .filter(Boolean)
})

const visibleTreeItemIds = computed(() => {
  const ids = []
  for (const group of treeGroups.value) {
    for (const subgroup of group.subgroups || []) {
      for (const item of subgroup.items || []) {
        ids.push(item.id)
      }
    }
  }
  return ids
})

const pageHealthSummary = computed(() => {
  const ids = visibleTreeItemIds.value
  let online = 0

  for (const id of ids) {
    if (healthState(id)?.ok) {
      online += 1
    }
  }

  return {
    online,
    total: ids.length,
  }
})

const activePageWidgetIds = computed(() => {
  if (!activePage.value) return []

  const ids = []
  for (const block of activePage.value.blocks || []) {
    if (!isWidgetBlock(block)) continue
    ids.push(...(block.widgets || []))
  }

  return Array.from(new Set(ids))
})

const sidebarIndicators = computed(() => resolveWidgets(activePageWidgetIds.value))

const sidebarIndicatorSummary = computed(() => {
  const total = sidebarIndicators.value.length
  if (!total) return 'нет данных'
  const largeCount = sidebarIndicators.value.filter((widget) => isLargeIndicator(widget)).length
  return `${total} · больших ${largeCount}`
})

const activePageGroupBlocks = computed(() => (activePage.value?.blocks || []).filter((block) => block?.type === 'groups'))

const activeIndicatorWidget = computed(() => {
  const widget = widgetById.value.get(activeIndicatorViewId.value)
  if (!widget || !isLargeIndicator(widget)) return null
  return activePageWidgetIds.value.includes(widget.id) ? widget : null
})

function applyTheme(theme) {
  if (!theme) return
  const root = document.documentElement

  if (theme.accent) {
    root.style.setProperty('--accent', theme.accent)
    root.style.setProperty('--accent-soft', theme.accent)
  }
  if (theme.background) {
    root.style.setProperty('--bg', theme.background)
  }
  if (theme.border) {
    root.style.setProperty('--border', theme.border)
  }
  if (theme.card) {
    root.style.setProperty('--surface', theme.card)
    root.style.setProperty('--surface-strong', theme.card)
  }

  root.style.setProperty('--glow-enabled', theme.glow === false ? '0' : '1')
}

function applyGrid(grid) {
  if (!grid) return
  const root = document.documentElement

  if (grid.gap != null) {
    root.style.setProperty('--grid-gap', `${Number(grid.gap)}px`)
  }
  if (grid.card_radius != null) {
    root.style.setProperty('--card-radius', `${Number(grid.card_radius)}px`)
  }
  if (grid.columns != null) {
    root.style.setProperty('--layout-columns', String(Number(grid.columns)))
  }
}

function isWidgetBlock(block) {
  return block?.type === 'widget_row' || block?.type === 'widget_grid'
}

function resolveWidgets(widgetIds = []) {
  return widgetIds
    .map((widgetId) => widgetById.value.get(widgetId))
    .filter(Boolean)
}

function isLargeIndicator(widget) {
  return LARGE_INDICATOR_TYPES.has(String(widget?.type || ''))
}

function indicatorPreviewEntries(widget) {
  return statListEntries(widget).slice(0, 2)
}

function openIndicatorView(widgetId) {
  const widget = sidebarIndicators.value.find((entry) => entry.id === widgetId)
  if (!widget || !isLargeIndicator(widget)) return
  activeIndicatorViewId.value = widget.id
}

function selectSidebarIndicator(widget) {
  if (isLargeIndicator(widget)) {
    openIndicatorView(widget.id)
  }
}

function resolveBlockGroups(groupIds = []) {
  const resolved = []

  for (const id of groupIds) {
    const group = groupById.value.get(id)
    if (group) {
      resolved.push({
        key: `group:${group.id}`,
        id: group.id,
        title: group.title,
        icon: group.icon || null,
        description: group.description || '',
        subgroups: group.subgroups || [],
      })
      continue
    }

    const subgroupRef = subgroupById.value.get(id)
    if (subgroupRef) {
      resolved.push({
        key: `subgroup:${subgroupRef.subgroup.id}`,
        id: subgroupRef.group.id,
        title: subgroupRef.group.title,
        icon: subgroupRef.group.icon || null,
        description: subgroupRef.group.description || '',
        subgroups: [subgroupRef.subgroup],
      })
    }
  }

  return resolved
}

function syncTreeGroupsState() {
  const activeKeys = new Set(treeGroups.value.map((group) => group.key))

  for (const key of Object.keys(expandedGroups)) {
    if (!activeKeys.has(key)) {
      delete expandedGroups[key]
    }
  }

  for (const group of treeGroups.value) {
    if (expandedGroups[group.key] == null) {
      expandedGroups[group.key] = true
    }
  }

  if (selectedNode.groupKey && !activeKeys.has(selectedNode.groupKey)) {
    clearSelectedNode()
  }
}

function clearSelectedNode() {
  selectedNode.groupKey = ''
  selectedNode.subgroupId = ''
  selectedNode.itemId = ''
}

function toggleGroupNode(groupKey) {
  expandedGroups[groupKey] = !isGroupExpanded(groupKey)
  selectedNode.groupKey = groupKey
  selectedNode.subgroupId = ''
  selectedNode.itemId = ''
}

function selectSubgroupNode(groupKey, subgroupId) {
  expandedGroups[groupKey] = true
  selectedNode.groupKey = groupKey
  selectedNode.subgroupId = subgroupId
  selectedNode.itemId = ''
}

function selectItemNode(groupKey, subgroupId, itemId) {
  expandedGroups[groupKey] = true
  selectedNode.groupKey = groupKey
  selectedNode.subgroupId = subgroupId
  selectedNode.itemId = itemId
}

function isGroupExpanded(groupKey) {
  return Boolean(expandedGroups[groupKey])
}

function isGroupSelected(groupKey) {
  return selectedNode.groupKey === groupKey && !selectedNode.subgroupId && !selectedNode.itemId
}

function isSubgroupSelected(groupKey, subgroupId) {
  return selectedNode.groupKey === groupKey && selectedNode.subgroupId === subgroupId && !selectedNode.itemId
}

function isItemSelected(itemId) {
  return selectedNode.itemId === itemId
}

function filteredBlockGroups(groupIds = []) {
  const groups = resolveBlockGroups(groupIds)

  if (!selectedNode.groupKey && !selectedNode.subgroupId && !selectedNode.itemId) {
    return groups
  }

  return groups
    .map((group) => {
      if (selectedNode.groupKey && group.key !== selectedNode.groupKey) {
        return null
      }

      let nextSubgroups = group.subgroups || []

      if (selectedNode.subgroupId) {
        nextSubgroups = nextSubgroups.filter((subgroup) => subgroup.id === selectedNode.subgroupId)
      }

      if (selectedNode.itemId) {
        nextSubgroups = nextSubgroups
          .map((subgroup) => ({
            ...subgroup,
            items: (subgroup.items || []).filter((item) => item.id === selectedNode.itemId),
          }))
          .filter((subgroup) => subgroup.items.length > 0)
      }

      if (!nextSubgroups.length) {
        return null
      }

      return {
        ...group,
        subgroups: nextSubgroups,
      }
    })
    .filter(Boolean)
}

function groupTotalItems(group) {
  return (group.subgroups || []).reduce((acc, subgroup) => acc + (subgroup.items || []).length, 0)
}

function groupOnlineItems(group) {
  let online = 0
  for (const subgroup of group.subgroups || []) {
    for (const item of subgroup.items || []) {
      if (healthState(item.id)?.ok) {
        online += 1
      }
    }
  }
  return online
}

function resolvePageIcon(page) {
  return pickSemanticIcon([page?.icon, page?.title, page?.id], LayoutDashboard)
}

function resolveGroupIcon(group) {
  return pickSemanticIcon([group?.icon, group?.title, group?.id, group?.description], FolderTree)
}

function resolveSubgroupIcon(subgroup) {
  return pickSemanticIcon([subgroup?.icon, subgroup?.title, subgroup?.id], Folder)
}

function resolveItemIcon(item) {
  return pickSemanticIcon(
    [item?.icon, item?.title, item?.id, item?.type, item?.url, ...(item?.tags || [])],
    item?.type === 'iframe' ? Globe : Link2
  )
}

function resolveWidgetIcon(widget) {
  return pickSemanticIcon([widget?.icon, widget?.title, widget?.id, widget?.type, widget?.data?.endpoint], Gauge)
}

function widgetState(widgetId) {
  return widgetStates[widgetId] || null
}

function actionKey(widgetId, actionId) {
  return `${widgetId}:${actionId}`
}

function isActionBusy(widgetId, actionId) {
  return Boolean(actionBusy[actionKey(widgetId, actionId)])
}

function resolveExpression(payload, expression) {
  if (!expression || typeof expression !== 'string') return null
  if (expression === '$') return payload
  if (!expression.startsWith('$.')) return null

  let current = payload
  const parts = expression.slice(2).split('.')

  for (const part of parts) {
    if (current == null) return null

    const arrayMatch = part.match(/^(.*)\[\*\]$/)
    if (arrayMatch) {
      const key = arrayMatch[1]
      const value = key ? current?.[key] : current
      return Array.isArray(value) ? value : []
    }

    current = current?.[part]
  }

  return current
}

function statCardValue(widget) {
  const payload = widgetState(widget.id)?.payload
  const value = resolveExpression(payload, widget.data?.mapping?.value)
  return value ?? '—'
}

function statCardSubtitle(widget) {
  const payload = widgetState(widget.id)?.payload
  const subtitle = resolveExpression(payload, widget.data?.mapping?.subtitle)
  return subtitle ?? ''
}

function statCardTrend(widget) {
  const payload = widgetState(widget.id)?.payload
  const trend = resolveExpression(payload, widget.data?.mapping?.trend)
  return trend ?? ''
}

function statListEntries(widget) {
  const payload = widgetState(widget.id)?.payload
  const mapping = widget.data?.mapping || {}
  const items = resolveExpression(payload, mapping.items)

  if (!Array.isArray(items)) return []

  return items.map((entry) => {
    const title = resolveExpression(entry, mapping.item_title) ?? '-'
    const value = resolveExpression(entry, mapping.item_value) ?? '-'
    return { title, value }
  })
}

function tableRows(widget) {
  const payload = widgetState(widget.id)?.payload
  const rowsExpression = widget.data?.mapping?.rows
  const fromExpression = resolveExpression(payload, rowsExpression)

  if (Array.isArray(fromExpression)) return fromExpression
  if (Array.isArray(payload)) return payload
  if (Array.isArray(payload?.items)) return payload.items
  return []
}

function normalizeEndpoint(endpoint) {
  if (!endpoint) return ''
  if (endpoint.startsWith('http://') || endpoint.startsWith('https://')) return endpoint
  if (endpoint.startsWith('/')) return endpoint
  return `/${endpoint}`
}

function resetWidgetPolling() {
  for (const timer of widgetIntervals.values()) {
    clearInterval(timer)
  }
  widgetIntervals.clear()
}

function stopHealthPolling() {
  if (healthPollTimer) {
    clearInterval(healthPollTimer)
    healthPollTimer = 0
  }
}

function healthState(itemId) {
  return healthStates[itemId] || null
}

function healthClass(itemId) {
  const state = healthState(itemId)
  if (!state) return 'unknown'
  return state.ok ? 'ok' : 'down'
}

function healthLabel(itemId) {
  const state = healthState(itemId)
  if (!state) return 'Проверка...'

  if (state.ok) {
    if (state.latency_ms != null) {
      return `Online • ${state.latency_ms} ms`
    }
    return 'Online'
  }

  if (state.error) {
    return `Offline • ${state.error}`
  }

  if (state.status_code != null) {
    return `Offline • HTTP ${state.status_code}`
  }

  return 'Offline'
}

async function refreshHealth() {
  const ids = visibleTreeItemIds.value
  if (!ids.length) return

  try {
    const payload = await fetchDashboardHealth(ids)
    for (const itemStatus of payload.items || []) {
      healthStates[itemStatus.item_id] = itemStatus
    }
  } catch {
    for (const id of ids) {
      if (!healthStates[id]) {
        healthStates[id] = {
          item_id: id,
          ok: false,
          checked_url: '',
          status_code: null,
          latency_ms: null,
          error: 'healthcheck unavailable',
        }
      }
    }
  }
}

async function startHealthPolling() {
  stopHealthPolling()
  await refreshHealth()

  healthPollTimer = window.setInterval(() => {
    refreshHealth()
  }, HEALTH_REFRESH_MS)
}

async function refreshWidget(widgetId) {
  const widget = widgetById.value.get(widgetId)
  if (!widget) return

  const endpoint = normalizeEndpoint(widget.data?.endpoint)
  if (!endpoint) return

  if (!widgetStates[widgetId]) {
    widgetStates[widgetId] = {
      loading: false,
      error: '',
      payload: null,
      lastUpdated: 0,
    }
  }

  const state = widgetStates[widgetId]
  state.loading = true
  state.error = ''

  try {
    state.payload = await requestJson(endpoint)
    state.lastUpdated = Date.now()
  } catch (error) {
    state.error = error?.message || 'Ошибка загрузки виджета'
  } finally {
    state.loading = false
  }
}

async function initWidgetPolling() {
  resetWidgetPolling()

  const initialLoads = []

  for (const widget of widgets.value) {
    initialLoads.push(refreshWidget(widget.id))

    if (!normalizeEndpoint(widget.data?.endpoint)) continue
    const intervalMs = Math.max(1, Number(widget.data?.refresh_sec || 0)) * 1000

    const timer = window.setInterval(() => {
      refreshWidget(widget.id)
    }, intervalMs)

    widgetIntervals.set(widget.id, timer)
  }

  await Promise.all(initialLoads)
}

async function runWidgetAction(widgetId, action) {
  const key = actionKey(widgetId, action.id)
  const endpoint = normalizeEndpoint(action.endpoint)
  if (!endpoint) return

  actionBusy[key] = true

  try {
    await requestJson(endpoint, {
      method: String(action.method || 'GET').toUpperCase(),
    })
    await refreshWidget(widgetId)
  } catch (error) {
    if (!widgetStates[widgetId]) {
      widgetStates[widgetId] = { loading: false, error: '', payload: null, lastUpdated: 0 }
    }
    widgetStates[widgetId].error = error?.message || 'Не удалось выполнить действие'
  } finally {
    actionBusy[key] = false
  }
}

async function loadConfig() {
  loadingConfig.value = true
  configError.value = ''

  try {
    const data = await fetchDashboardConfig()
    config.value = data

    if (!activePageId.value || !pages.value.some((page) => page.id === activePageId.value)) {
      activePageId.value = pages.value[0]?.id || ''
    }

    clearSelectedNode()
    syncTreeGroupsState()
    applyTheme(data?.ui?.theme)
    applyGrid(data?.ui?.grid)
    await initWidgetPolling()
    await startHealthPolling()
  } catch (error) {
    configError.value = error?.message || 'Не удалось загрузить dashboard-конфигурацию'
    config.value = null
    resetWidgetPolling()
    stopHealthPolling()
  } finally {
    loadingConfig.value = false
  }
}

async function openIframeItem(item) {
  const defaultSandbox = Boolean(config.value?.security?.iframe?.default_sandbox ?? true)
  const sandboxValue = item?.iframe?.sandbox

  iframeModal.open = true
  iframeModal.title = item.title
  iframeModal.src = ''
  iframeModal.error = ''
  iframeModal.loading = true
  iframeModal.sandbox = sandboxValue == null ? defaultSandbox : Boolean(sandboxValue)
  iframeModal.allow = Array.isArray(item?.iframe?.allow) ? item.iframe.allow.join('; ') : ''
  iframeModal.referrerPolicy = item?.iframe?.referrer_policy || ''

  try {
    const source = await fetchIframeSource(item.id)
    iframeModal.src = source.src
  } catch (error) {
    iframeModal.error = error?.message || 'Не удалось подготовить iframe'
  } finally {
    iframeModal.loading = false
  }
}

function closeIframeModal() {
  iframeModal.open = false
  iframeModal.title = ''
  iframeModal.src = ''
  iframeModal.error = ''
  iframeModal.loading = false
  iframeModal.sandbox = false
  iframeModal.allow = ''
  iframeModal.referrerPolicy = ''
}

function openLinkItem(item) {
  if (item.open === 'same_tab') {
    window.location.assign(item.url)
    return
  }
  window.open(item.url, '_blank', 'noopener,noreferrer')
}

function openItem(item) {
  if (item.type === 'iframe') {
    openIframeItem(item)
    return
  }

  openLinkItem(item)
}

async function copyUrl(url) {
  if (!navigator.clipboard?.writeText) return

  try {
    await navigator.clipboard.writeText(url)
  } catch {
    // ignore clipboard errors
  }
}

function initSidebarParticles() {
  if (!window.particlesJS) return

  window.particlesJS('sidebar-particles', {
    particles: {
      number: { value: 44, density: { enable: true, value_area: 700 } },
      color: { value: '#44e3cf' },
      shape: { type: 'circle' },
      opacity: { value: 0.22, random: true },
      size: { value: 2.2, random: true },
      line_linked: {
        enable: true,
        distance: 120,
        color: '#2dd4bf',
        opacity: 0.14,
        width: 1,
      },
      move: { enable: true, speed: 0.6 },
    },
    interactivity: {
      events: { onhover: { enable: false }, onclick: { enable: false }, resize: true },
    },
    retina_detect: true,
  })
}

watch(
  () => activePage.value?.id,
  () => {
    activeIndicatorViewId.value = ''
    treeFilter.value = ''
    clearSelectedNode()
    syncTreeGroupsState()
    refreshHealth()
  }
)

watch(
  () => activePageWidgetIds.value,
  (widgetIds) => {
    if (activeIndicatorViewId.value && !widgetIds.includes(activeIndicatorViewId.value)) {
      activeIndicatorViewId.value = ''
    }
  },
  { deep: true }
)

watch(
  () => treeGroups.value,
  () => {
    syncTreeGroupsState()
    refreshHealth()
  },
  { deep: true }
)

onMounted(async () => {
  initSidebarParticles()
  await loadConfig()
})

onBeforeUnmount(() => {
  resetWidgetPolling()
  stopHealthPolling()
})
</script>
