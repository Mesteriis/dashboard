import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  reactive,
  ref,
  watch,
} from "vue";
import {
  createDashboardHealthStream,
  fetchDashboardConfig,
  fetchDashboardHealth,
  fetchIframeSource,
  fetchLanScanState,
  requestJson,
  triggerLanScan,
  updateDashboardConfig,
} from "../services/dashboardApi.js";
import { ensureParticlesJs } from "../services/particlesLoader.js";
import {
  BRAND_ICON_BY_KEY,
  createBrandIcon,
} from "./dashboard/icons/brandIcons.js";
import { ICON_BY_KEY, ICON_RULES } from "./dashboard/icons/keywordIcons.js";
import {
  fromToken,
  normalizeIconToken,
  pickSemanticIcon,
  resolveGroupIcon as resolveGroupIconSemantic,
  resolveItemIcon as resolveItemIconSemantic,
  resolvePageIcon as resolvePageIconSemantic,
  resolveSubgroupIcon as resolveSubgroupIconSemantic,
  resolveWidgetIcon as resolveWidgetIconSemantic,
} from "./dashboard/icons/semanticResolver.js";
import {
  allItemIds,
  allSubgroupIds,
  ensurePageGroupsReference,
  findGroup,
  findSubgroup,
  isDirectGroupNode,
  makeUniqueId,
  moveGroup,
  moveItemBefore,
  moveItemToSubgroupEnd,
  moveSubgroup,
  normalizeId,
  normalizeLayoutBlocks,
} from "./dashboard/configTreeUtils.js";
import {
  ensureAbsoluteHttpUrl,
  originFromHttpUrl,
} from "./dashboard/urlUtils.js";

let dashboardStore = null;

export function useDashboardStore() {
  if (dashboardStore) {
    return dashboardStore;
  }
  const EMBLEM_SRC = "/static/img/emblem-mark.png";
  const HEALTH_REFRESH_MS = 30000;
  const HEALTH_REFRESH_DEGRADED_MS = 16000;
  const HEALTH_REFRESH_DOWN_MS = 9000;
  const HEALTH_STREAM_RECONNECT_MS = 3000;
  const DEGRADED_LATENCY_MS = 700;
  const LAN_SCAN_POLL_MS = 10000;
  const LAN_PAGE_ID = "lan";
  const LARGE_INDICATOR_TYPES = new Set(["stat_list", "table"]);
  const DEFAULT_ITEM_URL = "https://example.com";
  const SIDEBAR_PARTICLES_ID = "sidebar-particles";
  const HERO_TITLE_PARTICLES_ID = "hero-title-particles";
  const HERO_CONTROLS_PARTICLES_ID = "hero-controls-particles";
  const SIDEBAR_PARTICLES_CONFIG = {
    fps_limit: 58,
    particles: {
      number: { value: 88, density: { enable: true, value_area: 700 } },
      color: { value: "#6df6e2" },
      shape: { type: "circle" },
      opacity: { value: 0.36, random: true },
      size: { value: 2.4, random: true },
      line_linked: {
        enable: true,
        distance: 120,
        color: "#2dd4bf",
        opacity: 0.24,
        width: 1.2,
      },
      move: { enable: true, speed: 1.2 },
    },
    interactivity: {
      events: {
        onhover: { enable: false },
        onclick: { enable: false },
        resize: true,
      },
    },
    retina_detect: true,
  };
  const HERO_PARTICLES_CONFIG = {
    fps_limit: 58,
    particles: {
      number: { value: 92, density: { enable: true, value_area: 720 } },
      color: { value: "#6df6e2" },
      shape: { type: "circle" },
      opacity: { value: 0.4, random: true },
      size: { value: 2.4, random: true },
      line_linked: {
        enable: true,
        distance: 132,
        color: "#2dd4bf",
        opacity: 0.26,
        width: 1.2,
      },
      move: { enable: true, speed: 1.2 },
    },
    interactivity: {
      events: {
        onhover: { enable: false },
        onclick: { enable: false },
        resize: true,
      },
    },
    retina_detect: true,
  };
  const SERVICE_PRESENTATION_OPTIONS = Object.freeze([
    { value: "detailed", label: "Карточки" },
    { value: "tile", label: "Плитка" },
    { value: "icon", label: "Значки" },
  ]);
  const SERVICE_GROUPING_OPTIONS = Object.freeze([
    { value: "groups", label: "Только группы" },
    { value: "tags_in_groups", label: "Группы + теги" },
    { value: "tags", label: "Только теги" },
    { value: "flat", label: "Без групп (плитка)" },
  ]);
  const SIDEBAR_VIEW_SEQUENCE = ["detailed", "hidden"];
  const COMMAND_PALETTE_LIMIT = 18;
  const COMMAND_PALETTE_EMPTY_LIMIT = 10;
  const UI_STATE_STORAGE_KEY = "oko:dashboard-ui-state:v1";
  const SERVICE_CARD_VIEW_VALUES = new Set(
    SERVICE_PRESENTATION_OPTIONS.map((option) => option.value),
  );
  const SERVICE_GROUPING_VALUES = new Set(
    SERVICE_GROUPING_OPTIONS.map((option) => option.value),
  );

  function getLocalStorageSafe() {
    if (typeof window === "undefined") return null;
    try {
      return window.localStorage || null;
    } catch {
      return null;
    }
  }

  function loadPersistedUiState() {
    const storage = getLocalStorageSafe();
    if (!storage) return null;

    try {
      const raw = storage.getItem(UI_STATE_STORAGE_KEY);
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      return parsed && typeof parsed === "object" ? parsed : null;
    } catch {
      return null;
    }
  }

  function savePersistedUiState(snapshot) {
    const storage = getLocalStorageSafe();
    if (!storage) return;

    try {
      storage.setItem(UI_STATE_STORAGE_KEY, JSON.stringify(snapshot));
    } catch {
      // ignore localStorage quota/security errors
    }
  }

  function defaultItemEditorForm() {
    return {
      id: "",
      title: "",
      type: "link",
      url: DEFAULT_ITEM_URL,
      icon: "",
      siteInput: "",
      tagsInput: "",
      open: "new_tab",
      healthcheckEnabled: false,
      healthcheckUrl: "",
      healthcheckIntervalSec: 30,
      healthcheckTimeoutMs: 1500,
      iframeSandboxMode: "default",
      iframeAllowInput: "",
      iframeReferrerPolicy: "",
      authProfile: "",
    };
  }

  const config = ref(null);
  const loadingConfig = ref(true);
  const configError = ref("");
  const activePageId = ref("");
  const treeFilter = ref("");
  const statsExpanded = ref(false);
  const activeIndicatorViewId = ref("");
  const editMode = ref(false);
  const isDocumentVisible = ref(
    typeof document === "undefined"
      ? true
      : document.visibilityState !== "hidden",
  );
  const serviceCardView = ref("detailed");
  const serviceGroupingMode = ref("groups");
  const siteFilter = ref("all");
  const sidebarView = ref("detailed");
  const saveStatus = ref("idle");
  const saveError = ref("");
  const lanScanState = ref(null);
  const lanScanLoading = ref(false);
  const lanScanActionBusy = ref(false);
  const lanScanError = ref("");
  const commandPaletteOpen = ref(false);
  const commandPaletteQuery = ref("");
  const commandPaletteActiveIndex = ref(0);
  const settingsPanel = reactive({
    open: false,
  });
  const lanHostModal = reactive({
    open: false,
    host: null,
  });

  const widgetStates = reactive({});
  const actionBusy = reactive({});
  const widgetIntervals = new Map();
  let healthPollTimer = 0;
  let healthStream = null;
  let healthStreamReconnectTimer = 0;
  let saveStatusTimer = 0;
  let lanScanPollTimer = 0;
  let lanScanRefreshInFlight = false;
  let visibilitySyncInFlight = false;
  let particlesReinitRaf = 0;

  const selectedNode = reactive({
    groupKey: "",
    subgroupId: "",
    itemId: "",
  });

  const expandedGroups = reactive({});
  const healthStates = reactive({});
  const dragState = reactive({
    type: "",
    groupId: "",
    subgroupId: "",
    itemId: "",
  });
  const itemFaviconFailures = reactive({});
  const persistedUiState = loadPersistedUiState();

  if (persistedUiState) {
    const persistedCardView = String(persistedUiState.serviceCardView || "");
    if (SERVICE_CARD_VIEW_VALUES.has(persistedCardView)) {
      serviceCardView.value = persistedCardView;
    }

    const persistedGrouping = String(
      persistedUiState.serviceGroupingMode || "",
    );
    if (SERVICE_GROUPING_VALUES.has(persistedGrouping)) {
      serviceGroupingMode.value = persistedGrouping;
    }

    const persistedSidebarView = String(persistedUiState.sidebarView || "");
    if (SIDEBAR_VIEW_SEQUENCE.includes(persistedSidebarView)) {
      sidebarView.value = persistedSidebarView;
    }

    const persistedSiteFilter = String(persistedUiState.siteFilter || "")
      .trim()
      .toLowerCase();
    siteFilter.value = persistedSiteFilter || "all";
    activePageId.value = String(persistedUiState.activePageId || "");
    treeFilter.value = String(persistedUiState.treeFilter || "");
    activeIndicatorViewId.value = String(
      persistedUiState.activeIndicatorViewId || "",
    );
    statsExpanded.value = Boolean(persistedUiState.statsExpanded);
    editMode.value = Boolean(persistedUiState.editMode);
    settingsPanel.open = Boolean(persistedUiState.settingsPanelOpen);

    const persistedSelectedNode = persistedUiState.selectedNode;
    if (persistedSelectedNode && typeof persistedSelectedNode === "object") {
      selectedNode.groupKey = String(persistedSelectedNode.groupKey || "");
      selectedNode.subgroupId = String(persistedSelectedNode.subgroupId || "");
      selectedNode.itemId = String(persistedSelectedNode.itemId || "");
    }

    const persistedExpandedGroups = persistedUiState.expandedGroups;
    if (
      persistedExpandedGroups &&
      typeof persistedExpandedGroups === "object"
    ) {
      for (const [groupKey, expanded] of Object.entries(
        persistedExpandedGroups,
      )) {
        const normalizedGroupKey = String(groupKey || "");
        if (!normalizedGroupKey) continue;
        expandedGroups[normalizedGroupKey] = Boolean(expanded);
      }
    }
  }

  const iframeModal = reactive({
    open: false,
    title: "",
    src: "",
    allow: "",
    sandbox: false,
    referrerPolicy: "",
    loading: false,
    error: "",
  });

  const itemEditor = reactive({
    open: false,
    mode: "create",
    groupId: "",
    subgroupId: "",
    originalItemId: "",
    submitting: false,
    error: "",
    form: defaultItemEditorForm(),
  });

  const pages = computed(() => {
    if (!config.value) return [];
    const configured = config.value?.layout?.pages || [];
    if (configured.some((page) => page.id === LAN_PAGE_ID)) {
      return configured;
    }

    return [
      ...configured,
      {
        id: LAN_PAGE_ID,
        title: "LAN",
        icon: "network",
        blocks: [],
      },
    ];
  });
  const widgets = computed(() => config.value?.widgets || []);
  const authProfileOptions = computed(
    () => config.value?.security?.auth_profiles || [],
  );

  const appTitle = computed(() => config.value?.app?.title || "Oko");
  const appTagline = computed(
    () => config.value?.app?.tagline || "Your Infrastructure in Sight",
  );
  const servicePresentationOptions = computed(
    () => SERVICE_PRESENTATION_OPTIONS,
  );
  const serviceGroupingOptions = computed(() => SERVICE_GROUPING_OPTIONS);
  const isIconCardView = computed(() => serviceCardView.value === "icon");
  const isTileCardView = computed(() => serviceCardView.value === "tile");
  const isCompactServiceCardView = computed(
    () => isIconCardView.value || isTileCardView.value,
  );
  const isSidebarDetailed = computed(() => sidebarView.value !== "hidden");
  const isSidebarHidden = computed(() => sidebarView.value === "hidden");
  const isSidebarIconOnly = computed(() => false);
  const sidebarViewToggleTitle = computed(() => {
    if (isSidebarDetailed.value)
      return "Режим меню: полное. Нажмите, чтобы скрыть меню";
    return "Режим меню: скрыто. Нажмите, чтобы вернуть полное меню";
  });
  const lanHosts = computed(() => lanScanState.value?.result?.hosts || []);
  const lanCidrsLabel = computed(() => {
    const cidrs = lanScanState.value?.result?.scanned_cidrs || [];
    return cidrs.length ? cidrs.join(", ") : "нет данных";
  });
  const saveStatusLabel = computed(() => {
    if (saveStatus.value === "saving") return "Сохранение...";
    if (saveStatus.value === "saved") return "Сохранено";
    if (saveStatus.value === "error") return "Ошибка сохранения";
    return editMode.value ? "Готово" : "Сохранение выключено";
  });
  const siteFilterOptions = computed(() => {
    const sitesMap = new Map();
    for (const group of config.value?.groups || []) {
      for (const subgroup of group.subgroups || []) {
        for (const item of subgroup.items || []) {
          const site = resolveItemSite(item, group);
          if (!site) continue;
          const normalized = site.toLowerCase();
          if (!sitesMap.has(normalized)) {
            sitesMap.set(normalized, site);
          }
        }
      }
    }

    const sites = Array.from(sitesMap.entries()).sort((left, right) =>
      left[1].localeCompare(right[1], "ru", { sensitivity: "base" }),
    );

    return [
      { value: "all", label: "Все sites" },
      ...sites.map(([value, label]) => ({ value, label })),
    ];
  });

  const widgetById = computed(() => {
    const map = new Map();
    for (const widget of widgets.value) {
      map.set(widget.id, widget);
    }
    return map;
  });

  const groupById = computed(() => {
    const map = new Map();
    for (const group of config.value?.groups || []) {
      map.set(group.id, group);
    }
    return map;
  });

  const subgroupById = computed(() => {
    const map = new Map();
    for (const group of config.value?.groups || []) {
      for (const subgroup of group.subgroups || []) {
        map.set(subgroup.id, { group, subgroup });
      }
    }
    return map;
  });

  const pageByBlockGroupId = computed(() => {
    const map = new Map();
    for (const page of pages.value) {
      for (const block of page.blocks || []) {
        if (block?.type !== "groups") continue;
        for (const blockGroupId of block.group_ids || []) {
          if (!map.has(blockGroupId)) {
            map.set(blockGroupId, page.id);
          }
        }
      }
    }
    return map;
  });

  const itemIpById = computed(() => {
    const map = new Map();
    for (const host of lanHosts.value || []) {
      const ip = String(host?.ip || "").trim();
      if (!ip) continue;

      for (const mappedItem of host?.dashboard_items || []) {
        const itemId = String(mappedItem?.id || "").trim();
        if (itemId && !map.has(itemId)) {
          map.set(itemId, ip);
        }
      }
    }
    return map;
  });

  const commandPaletteEntries = computed(() => {
    const entries = [];
    const pageMap = pageByBlockGroupId.value;

    entries.push({
      id: "action:open-settings-panel",
      type: "action",
      action: "open_settings_panel",
      item: null,
      title: "Открыть панель настроек",
      titleLower: "открыть панель настроек",
      host: "",
      ip: "",
      site: "",
      tagsLower: [],
      groupId: "",
      groupKey: "",
      groupTitle: "Команда",
      subgroupId: "",
      subgroupTitle: "Интерфейс",
      pageId: "",
      searchBlob:
        "открыть панель настроек settings ui интерфейс control panel параметры фильтры",
    });

    for (const group of config.value?.groups || []) {
      for (const subgroup of group.subgroups || []) {
        for (const item of subgroup.items || []) {
          const host = safeUrlHost(item?.url);
          const ip = itemIpById.value.get(item.id) || "";
          const tags = (item.tags || [])
            .map((tag) => String(tag || "").trim())
            .filter(Boolean);
          const site = resolveItemSite(item, group);
          if (
            siteFilter.value !== "all" &&
            site.toLowerCase() !== siteFilter.value
          ) {
            continue;
          }
          const pageId =
            pageMap.get(group.id) || pageMap.get(subgroup.id) || "";

          const title = String(item.title || "").trim();
          const searchBlob = [
            title,
            String(item.id || ""),
            String(item.url || ""),
            host,
            ip,
            site,
            String(group.title || ""),
            String(subgroup.title || ""),
            ...tags,
          ]
            .join(" ")
            .toLowerCase();

          entries.push({
            id: item.id,
            type: "item",
            action: "",
            item,
            title,
            titleLower: title.toLowerCase(),
            host: host.toLowerCase(),
            ip: ip.toLowerCase(),
            site: site.toLowerCase(),
            tagsLower: tags.map((tag) => tag.toLowerCase()),
            groupId: group.id,
            groupKey: `group:${group.id}`,
            groupTitle: String(group.title || ""),
            subgroupId: subgroup.id,
            subgroupTitle: String(subgroup.title || ""),
            pageId,
            searchBlob,
          });
        }
      }
    }

    return entries;
  });

  const commandPaletteResults = computed(() => {
    const query = String(commandPaletteQuery.value || "")
      .trim()
      .toLowerCase();
    const entries = commandPaletteEntries.value;
    if (!query) {
      const actionEntries = entries.filter((entry) => entry.type === "action");
      const itemEntries = entries
        .filter((entry) => entry.type !== "action")
        .slice()
        .sort((left, right) =>
          left.title.localeCompare(right.title, "ru", { sensitivity: "base" }),
        );
      return [...actionEntries, ...itemEntries].slice(
        0,
        COMMAND_PALETTE_EMPTY_LIMIT,
      );
    }

    const tokens = query.split(/\s+/).filter(Boolean);
    const scored = [];
    for (const entry of entries) {
      let score = 0;
      let matched = true;

      for (const token of tokens) {
        if (!entry.searchBlob.includes(token)) {
          matched = false;
          break;
        }

        if (entry.titleLower.startsWith(token)) score += 12;
        else if (entry.titleLower.includes(token)) score += 8;
        if (entry.host.startsWith(token)) score += 7;
        else if (entry.host.includes(token)) score += 4;
        if (entry.ip === token) score += 14;
        else if (entry.ip.includes(token)) score += 6;
        if (entry.site && entry.site.includes(token)) score += 5;
        if (entry.tagsLower.some((tag) => tag.includes(token))) score += 3;
      }

      if (matched) {
        scored.push({ entry, score });
      }
    }

    scored.sort((left, right) => {
      if (right.score !== left.score) return right.score - left.score;
      return left.entry.title.localeCompare(right.entry.title, "ru", {
        sensitivity: "base",
      });
    });
    return scored.slice(0, COMMAND_PALETTE_LIMIT).map((record) => record.entry);
  });

  const activeCommandPaletteEntry = computed(
    () => commandPaletteResults.value[commandPaletteActiveIndex.value] || null,
  );

  const activePage = computed(
    () =>
      pages.value.find((page) => page.id === activePageId.value) ||
      pages.value[0] ||
      null,
  );
  const isLanPage = computed(() => activePage.value?.id === LAN_PAGE_ID);

  const treeGroups = computed(() => {
    if (!activePage.value) return [];

    const groupIds = [];
    for (const block of activePage.value.blocks || []) {
      if (block?.type === "groups") {
        groupIds.push(...(block.group_ids || []));
      }
    }

    return resolveBlockGroups(groupIds);
  });

  const filteredTreeGroups = computed(() => {
    const bySite = filterGroupsBySite(treeGroups.value);
    const query = treeFilter.value.trim().toLowerCase();
    if (!query) return bySite;

    return bySite
      .map((group) => {
        const groupMatches =
          String(group.title || "")
            .toLowerCase()
            .includes(query) ||
          String(group.description || "")
            .toLowerCase()
            .includes(query);

        if (groupMatches) {
          return {
            ...group,
            subgroups: group.subgroups || [],
          };
        }

        const matchedSubgroups = (group.subgroups || [])
          .map((subgroup) => {
            const subgroupMatches = String(subgroup.title || "")
              .toLowerCase()
              .includes(query);
            if (subgroupMatches) {
              return {
                ...subgroup,
                items: subgroup.items || [],
              };
            }

            const matchedItems = (subgroup.items || []).filter((item) => {
              const inTitle = String(item.title || "")
                .toLowerCase()
                .includes(query);
              const inUrl = String(item.url || "")
                .toLowerCase()
                .includes(query);
              const inTags = (item.tags || []).some((tag) =>
                String(tag).toLowerCase().includes(query),
              );
              const inSite = resolveItemSite(item, group)
                .toLowerCase()
                .includes(query);
              return inTitle || inUrl || inTags || inSite;
            });

            if (!matchedItems.length) return null;
            return {
              ...subgroup,
              items: matchedItems,
            };
          })
          .filter(Boolean);

        if (!matchedSubgroups.length) return null;
        return {
          ...group,
          subgroups: matchedSubgroups,
        };
      })
      .filter(Boolean);
  });

  const sidebarIconNodes = computed(() => {
    const nodes = [];

    for (const group of filteredTreeGroups.value) {
      nodes.push({
        key: `group:${group.key}`,
        type: "group",
        groupKey: group.key,
        group,
      });

      for (const subgroup of group.subgroups || []) {
        nodes.push({
          key: `subgroup:${group.key}:${subgroup.id}`,
          type: "subgroup",
          groupKey: group.key,
          subgroupId: subgroup.id,
          subgroup,
        });
      }
    }

    return nodes;
  });

  const visibleTreeItemIds = computed(() => {
    const ids = [];
    for (const group of treeGroups.value) {
      for (const subgroup of group.subgroups || []) {
        for (const item of subgroup.items || []) {
          ids.push(item.id);
        }
      }
    }
    return ids;
  });

  const pageHealthSummary = computed(() => {
    const ids = visibleTreeItemIds.value;
    let online = 0;

    for (const id of ids) {
      if (healthState(id)?.ok) {
        online += 1;
      }
    }

    return {
      online,
      total: ids.length,
    };
  });

  const activePageWidgetIds = computed(() => {
    if (!activePage.value) return [];

    const ids = [];
    for (const block of activePage.value.blocks || []) {
      if (!isWidgetBlock(block)) continue;
      ids.push(...(block.widgets || []));
    }

    return Array.from(new Set(ids));
  });

  const sidebarIndicators = computed(() =>
    resolveWidgets(activePageWidgetIds.value),
  );

  const sidebarIndicatorSummary = computed(() => {
    const total = sidebarIndicators.value.length;
    if (!total) return "нет данных";
    const largeCount = sidebarIndicators.value.filter((widget) =>
      isLargeIndicator(widget),
    ).length;
    return `${total} · больших ${largeCount}`;
  });

  const activePageGroupBlocks = computed(() =>
    (activePage.value?.blocks || []).filter(
      (block) => block?.type === "groups",
    ),
  );

  const activeIndicatorWidget = computed(() => {
    const widget = widgetById.value.get(activeIndicatorViewId.value);
    if (!widget || !isLargeIndicator(widget)) return null;
    return activePageWidgetIds.value.includes(widget.id) ? widget : null;
  });

  function applyTheme(theme) {
    if (!theme) return;
    const root = document.documentElement;

    if (theme.accent) {
      root.style.setProperty("--accent", theme.accent);
      root.style.setProperty("--accent-soft", theme.accent);
    }
    if (theme.background) {
      root.style.setProperty("--bg", theme.background);
    }
    if (theme.border) {
      root.style.setProperty("--border", theme.border);
    }
    if (theme.card) {
      root.style.setProperty("--surface", theme.card);
      root.style.setProperty("--surface-strong", theme.card);
    }

    root.style.setProperty("--glow-enabled", theme.glow === false ? "0" : "1");
  }

  function applyGrid(grid) {
    if (!grid) return;
    const root = document.documentElement;

    if (grid.gap != null) {
      root.style.setProperty("--grid-gap", `${Number(grid.gap)}px`);
    }
    if (grid.card_radius != null) {
      root.style.setProperty("--card-radius", `${Number(grid.card_radius)}px`);
    }
    if (grid.columns != null) {
      root.style.setProperty("--layout-columns", String(Number(grid.columns)));
    }
  }

  function toggleEditMode() {
    editMode.value = !editMode.value;
    saveError.value = "";
    if (!editMode.value) {
      clearDragState();
    }
  }

  function toggleServiceCardView() {
    if (serviceCardView.value === "detailed") {
      serviceCardView.value = "tile";
      return;
    }

    if (serviceCardView.value === "tile") {
      serviceCardView.value = "icon";
      return;
    }

    serviceCardView.value = "detailed";
  }

  function toggleSidebarView() {
    if (sidebarView.value !== "detailed" && sidebarView.value !== "hidden") {
      sidebarView.value = "detailed";
    }
    const currentIndex = SIDEBAR_VIEW_SEQUENCE.indexOf(sidebarView.value);
    const safeIndex = currentIndex >= 0 ? currentIndex : 0;
    const nextIndex = (safeIndex + 1) % SIDEBAR_VIEW_SEQUENCE.length;
    sidebarView.value = SIDEBAR_VIEW_SEQUENCE[nextIndex];

    if (!isSidebarDetailed.value) {
      treeFilter.value = "";
      clearSelectedNode();
    }

    if (isSidebarHidden.value) {
      serviceGroupingMode.value = "flat";
    }
  }

  function isSidebarIconActive(node) {
    if (!node) return false;
    if (node.type === "group") return isGroupSelected(node.groupKey);
    if (node.type === "subgroup")
      return isSubgroupSelected(node.groupKey, node.subgroupId);
    return false;
  }

  function sidebarIconNodeTitle(node) {
    if (!node) return "";
    if (node.type === "group") {
      return `Группа: ${node.group?.title || ""}`;
    }
    if (node.type === "subgroup") {
      return `Подгруппа: ${node.subgroup?.title || ""}`;
    }
    return "";
  }

  function selectSidebarIconNode(node) {
    if (!node) return;

    if (node.type === "group") {
      expandedGroups[node.groupKey] = true;
      selectedNode.groupKey = node.groupKey;
      selectedNode.subgroupId = "";
      selectedNode.itemId = "";
      return;
    }

    if (node.type === "subgroup") {
      selectSubgroupNode(node.groupKey, node.subgroupId);
    }
  }

  function onItemCardClick(groupKey, subgroupId, item) {
    if (!isCompactServiceCardView.value) return;
    const targetGroupKey = item?.__originGroupKey || groupKey;
    const targetSubgroupId = item?.__originSubgroupId || subgroupId;
    selectItemNode(targetGroupKey, targetSubgroupId, item.id);
    openItem(item);
  }

  function cloneConfig(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function ensureAbsoluteUrl(rawValue) {
    return ensureAbsoluteHttpUrl(rawValue);
  }

  async function persistConfig() {
    if (!config.value) return;

    saveStatus.value = "saving";
    saveError.value = "";

    try {
      const response = await updateDashboardConfig(config.value);
      config.value = response.config;

      if (
        !activePageId.value ||
        !pages.value.some((page) => page.id === activePageId.value)
      ) {
        activePageId.value = pages.value[0]?.id || "";
      }

      saveStatus.value = "saved";
      if (saveStatusTimer) {
        clearTimeout(saveStatusTimer);
      }

      saveStatusTimer = window.setTimeout(() => {
        if (saveStatus.value === "saved") {
          saveStatus.value = "idle";
        }
      }, 1400);
    } catch (error) {
      saveStatus.value = "error";
      saveError.value = error?.message || "Ошибка сохранения YAML";
      throw error;
    }
  }

  async function applyConfigMutation(mutator) {
    if (!config.value) return false;

    const snapshot = cloneConfig(config.value);

    try {
      const result = mutator(config.value);
      if (result === false) return false;

      normalizeLayoutBlocks(config.value);
      syncTreeGroupsState();
      await persistConfig();
      return true;
    } catch (error) {
      config.value = snapshot;
      saveStatus.value = "error";
      saveError.value = error?.message || "Не удалось применить изменения";
      return false;
    }
  }

  function buildDefaultItem(itemId, title) {
    return {
      id: itemId,
      type: "link",
      title,
      url: DEFAULT_ITEM_URL,
      icon: null,
      site: null,
      tags: [],
      open: "new_tab",
    };
  }

  async function addGroup() {
    if (!editMode.value || !config.value) return;

    const title = window.prompt("Название новой группы", "Новая группа");
    if (title == null) return;
    const normalizedTitle = title.trim();
    if (!normalizedTitle) return;

    await applyConfigMutation((cfg) => {
      const groupIds = new Set((cfg.groups || []).map((group) => group.id));
      const subgroupIds = allSubgroupIds(cfg);
      const itemIds = allItemIds(cfg);

      const groupId = makeUniqueId(normalizedTitle, groupIds);
      const subgroupId = makeUniqueId(`${groupId}-core`, subgroupIds);
      const itemId = makeUniqueId(`${groupId}-service`, itemIds);

      cfg.groups.push({
        id: groupId,
        title: normalizedTitle,
        icon: "folder",
        description: "",
        layout: "auto",
        subgroups: [
          {
            id: subgroupId,
            title: "Core",
            items: [buildDefaultItem(itemId, "Новый сервис")],
          },
        ],
      });

      ensurePageGroupsReference(cfg, activePageId.value, groupId);
      expandedGroups[`group:${groupId}`] = true;
      selectedNode.groupKey = `group:${groupId}`;
      selectedNode.subgroupId = subgroupId;
      selectedNode.itemId = itemId;
    });
  }

  async function addSubgroup(groupId) {
    if (!editMode.value || !config.value) return;

    const title = window.prompt("Название подгруппы", "Новая подгруппа");
    if (title == null) return;
    const normalizedTitle = title.trim();
    if (!normalizedTitle) return;

    await applyConfigMutation((cfg) => {
      const group = findGroup(cfg, groupId);
      if (!group) throw new Error(`Группа '${groupId}' не найдена`);

      const subgroupIds = allSubgroupIds(cfg);
      const itemIds = allItemIds(cfg);
      const subgroupId = makeUniqueId(
        `${groupId}-${normalizedTitle}`,
        subgroupIds,
      );
      const itemId = makeUniqueId(`${subgroupId}-service`, itemIds);

      group.subgroups.push({
        id: subgroupId,
        title: normalizedTitle,
        items: [buildDefaultItem(itemId, "Новый сервис")],
      });

      expandedGroups[`group:${groupId}`] = true;
      selectedNode.groupKey = `group:${groupId}`;
      selectedNode.subgroupId = subgroupId;
      selectedNode.itemId = itemId;
    });
  }

  async function addItem(groupId, subgroupId) {
    if (!editMode.value || !config.value) return;
    openCreateItemEditor(groupId, subgroupId);
  }

  function normalizeStringList(rawValue) {
    return String(rawValue || "")
      .split(",")
      .map((value) => value.trim())
      .filter(Boolean);
  }

  function clampNumber(value, fallback, min, max) {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) return fallback;
    const integerValue = Math.trunc(numeric);
    return Math.min(max, Math.max(min, integerValue));
  }

  function closeItemEditor(force = false) {
    if (itemEditor.submitting && !force) return;

    itemEditor.open = false;
    itemEditor.mode = "create";
    itemEditor.groupId = "";
    itemEditor.subgroupId = "";
    itemEditor.originalItemId = "";
    itemEditor.error = "";
    itemEditor.submitting = false;
    itemEditor.form = defaultItemEditorForm();
  }

  function openCreateItemEditor(groupId, subgroupId) {
    const subgroup = findSubgroup(config.value, groupId, subgroupId);
    if (!subgroup) {
      saveStatus.value = "error";
      saveError.value = `Подгруппа '${subgroupId}' не найдена`;
      return;
    }

    itemEditor.open = true;
    itemEditor.mode = "create";
    itemEditor.groupId = groupId;
    itemEditor.subgroupId = subgroupId;
    itemEditor.originalItemId = "";
    itemEditor.error = "";
    itemEditor.submitting = false;
    itemEditor.form = defaultItemEditorForm();
  }

  function openEditItemEditor(groupId, subgroupId, itemId) {
    const subgroup = findSubgroup(config.value, groupId, subgroupId);
    const item = (subgroup?.items || []).find((entry) => entry.id === itemId);
    if (!subgroup || !item) {
      saveStatus.value = "error";
      saveError.value = `Элемент '${itemId}' не найден`;
      return;
    }

    itemEditor.open = true;
    itemEditor.mode = "edit";
    itemEditor.groupId = groupId;
    itemEditor.subgroupId = subgroupId;
    itemEditor.originalItemId = itemId;
    itemEditor.error = "";
    itemEditor.submitting = false;
    itemEditor.form = {
      id: item.id,
      title: item.title,
      type: item.type,
      url: String(item.url || DEFAULT_ITEM_URL),
      icon: item.icon || "",
      siteInput: String(item.site || ""),
      tagsInput: (item.tags || []).join(", "),
      open: item.open || "new_tab",
      healthcheckEnabled: Boolean(item.type === "link" && item.healthcheck),
      healthcheckUrl:
        item.type === "link" && item.healthcheck
          ? String(item.healthcheck.url)
          : String(item.url || DEFAULT_ITEM_URL),
      healthcheckIntervalSec:
        item.type === "link" && item.healthcheck
          ? Number(item.healthcheck.interval_sec || 30)
          : 30,
      healthcheckTimeoutMs:
        item.type === "link" && item.healthcheck
          ? Number(item.healthcheck.timeout_ms || 1500)
          : 1500,
      iframeSandboxMode:
        item.type === "iframe"
          ? item.iframe?.sandbox == null
            ? "default"
            : item.iframe.sandbox
              ? "enabled"
              : "disabled"
          : "default",
      iframeAllowInput:
        item.type === "iframe" ? (item.iframe?.allow || []).join(", ") : "",
      iframeReferrerPolicy:
        item.type === "iframe" ? item.iframe?.referrer_policy || "" : "",
      authProfile: item.type === "iframe" ? item.auth_profile || "" : "",
    };
  }

  function buildItemFromEditorForm(cfg) {
    const form = itemEditor.form;
    const title = String(form.title || "").trim();
    if (!title) {
      throw new Error("Название сервиса обязательно");
    }

    const normalizedType = String(form.type || "")
      .trim()
      .toLowerCase();
    if (!["link", "iframe"].includes(normalizedType)) {
      throw new Error("Тип сервиса должен быть 'link' или 'iframe'");
    }

    const openMode = String(form.open || "new_tab");
    if (!["new_tab", "same_tab"].includes(openMode)) {
      throw new Error("Параметр open должен быть 'new_tab' или 'same_tab'");
    }

    const url = ensureAbsoluteUrl(form.url || DEFAULT_ITEM_URL);
    const itemIds = allItemIds(cfg);
    if (itemEditor.mode === "edit") {
      itemIds.delete(itemEditor.originalItemId);
    }

    const rawId = String(form.id || "").trim();
    const generatedBase = `${itemEditor.subgroupId}-${title}`;
    const normalizedId = normalizeId(rawId || generatedBase, "service");
    const nextId = rawId ? normalizedId : makeUniqueId(normalizedId, itemIds);

    if (rawId && itemIds.has(nextId)) {
      throw new Error(`ID '${nextId}' уже существует`);
    }

    const baseItem = {
      id: nextId,
      type: normalizedType,
      title,
      url,
      icon: String(form.icon || "").trim() || null,
      site: String(form.siteInput || "").trim() || null,
      tags: normalizeStringList(form.tagsInput),
      open: openMode,
    };

    if (normalizedType === "link") {
      const linkItem = { ...baseItem };

      if (form.healthcheckEnabled) {
        const healthcheckUrl = ensureAbsoluteUrl(form.healthcheckUrl || url);
        linkItem.healthcheck = {
          type: "http",
          url: healthcheckUrl,
          interval_sec: clampNumber(form.healthcheckIntervalSec, 30, 1, 3600),
          timeout_ms: clampNumber(form.healthcheckTimeoutMs, 1500, 100, 120000),
        };
      }

      return linkItem;
    }

    const sandboxMode = String(form.iframeSandboxMode || "default");
    let sandboxValue = null;
    if (sandboxMode === "enabled") sandboxValue = true;
    if (sandboxMode === "disabled") sandboxValue = false;

    const authProfile = String(form.authProfile || "").trim();
    if (
      authProfile &&
      !authProfileOptions.value.some((profile) => profile.id === authProfile)
    ) {
      throw new Error(`Auth profile '${authProfile}' не найден`);
    }

    const iframeItem = {
      ...baseItem,
      iframe: {
        sandbox: sandboxValue,
        allow: normalizeStringList(form.iframeAllowInput),
        referrer_policy: String(form.iframeReferrerPolicy || "").trim() || null,
      },
    };

    if (authProfile) {
      iframeItem.auth_profile = authProfile;
    }

    return iframeItem;
  }

  async function submitItemEditor() {
    if (!itemEditor.open || itemEditor.submitting || !config.value) return;

    itemEditor.submitting = true;
    itemEditor.error = "";

    const success = await applyConfigMutation((cfg) => {
      const subgroup = findSubgroup(
        cfg,
        itemEditor.groupId,
        itemEditor.subgroupId,
      );
      if (!subgroup) {
        throw new Error(`Подгруппа '${itemEditor.subgroupId}' не найдена`);
      }

      const nextItem = buildItemFromEditorForm(cfg);

      if (itemEditor.mode === "create") {
        subgroup.items.push(nextItem);
        selectedNode.groupKey = `group:${itemEditor.groupId}`;
        selectedNode.subgroupId = itemEditor.subgroupId;
        selectedNode.itemId = nextItem.id;
        return true;
      }

      const index = (subgroup.items || []).findIndex(
        (entry) => entry.id === itemEditor.originalItemId,
      );
      if (index < 0) {
        throw new Error(`Элемент '${itemEditor.originalItemId}' не найден`);
      }

      subgroup.items.splice(index, 1, nextItem);
      selectedNode.groupKey = `group:${itemEditor.groupId}`;
      selectedNode.subgroupId = itemEditor.subgroupId;
      if (
        selectedNode.itemId === itemEditor.originalItemId ||
        !selectedNode.itemId
      ) {
        selectedNode.itemId = nextItem.id;
      }
      return true;
    });

    itemEditor.submitting = false;
    if (success) {
      closeItemEditor(true);
    } else {
      itemEditor.error = saveError.value || "Не удалось сохранить сервис";
    }
  }

  async function editGroup(groupId) {
    if (!editMode.value || !config.value) return;

    const group = findGroup(config.value, groupId);
    if (!group) return;

    const nextTitle = window.prompt("Название группы", group.title);
    if (nextTitle == null) return;

    const nextDescription = window.prompt(
      "Описание группы",
      group.description || "",
    );
    if (nextDescription == null) return;

    const nextLayout = window.prompt(
      "Режим группы (auto | full | inline)",
      group.layout || "auto",
    );
    if (nextLayout == null) return;

    await applyConfigMutation((cfg) => {
      const target = findGroup(cfg, groupId);
      if (!target) throw new Error(`Группа '${groupId}' не найдена`);

      const normalizedLayout =
        String(nextLayout || "")
          .trim()
          .toLowerCase() || "auto";
      if (!["auto", "full", "inline"].includes(normalizedLayout)) {
        throw new Error("Режим группы должен быть 'auto', 'full' или 'inline'");
      }

      target.title = nextTitle.trim() || target.title;
      target.description = nextDescription.trim();
      target.layout = normalizedLayout;
    });
  }

  async function editSubgroup(groupId, subgroupId) {
    if (!editMode.value || !config.value) return;

    const subgroup = findSubgroup(config.value, groupId, subgroupId);
    if (!subgroup) return;

    const nextTitle = window.prompt("Название подгруппы", subgroup.title);
    if (nextTitle == null) return;

    await applyConfigMutation((cfg) => {
      const target = findSubgroup(cfg, groupId, subgroupId);
      if (!target) throw new Error(`Подгруппа '${subgroupId}' не найдена`);

      target.title = nextTitle.trim() || target.title;
    });
  }

  async function editItem(groupId, subgroupId, itemId) {
    if (!editMode.value || !config.value) return;
    openEditItemEditor(groupId, subgroupId, itemId);
  }

  async function removeGroup(groupId) {
    if (!editMode.value || !config.value) return;

    const group = findGroup(config.value, groupId);
    if (!group) return;

    if (config.value.groups.length <= 1) {
      saveStatus.value = "error";
      saveError.value = "Нельзя удалить последнюю группу.";
      return;
    }

    if (!window.confirm(`Удалить группу "${group.title}"?`)) return;

    await applyConfigMutation((cfg) => {
      const index = (cfg.groups || []).findIndex(
        (entry) => entry.id === groupId,
      );
      if (index < 0) return false;
      cfg.groups.splice(index, 1);

      selectedNode.groupKey = "";
      selectedNode.subgroupId = "";
      selectedNode.itemId = "";
    });
  }

  async function removeSubgroup(groupId, subgroupId) {
    if (!editMode.value || !config.value) return;

    const group = findGroup(config.value, groupId);
    const subgroup = (group?.subgroups || []).find(
      (entry) => entry.id === subgroupId,
    );
    if (!group || !subgroup) return;

    if (group.subgroups.length <= 1) {
      saveStatus.value = "error";
      saveError.value = "В группе должна остаться хотя бы одна подгруппа.";
      return;
    }

    if (!window.confirm(`Удалить подгруппу "${subgroup.title}"?`)) return;

    await applyConfigMutation((cfg) => {
      const targetGroup = findGroup(cfg, groupId);
      if (!targetGroup) return false;

      const index = (targetGroup.subgroups || []).findIndex(
        (entry) => entry.id === subgroupId,
      );
      if (index < 0) return false;
      targetGroup.subgroups.splice(index, 1);

      selectedNode.subgroupId = "";
      selectedNode.itemId = "";
    });
  }

  async function removeItem(groupId, subgroupId, itemId) {
    if (!editMode.value || !config.value) return;

    const subgroup = findSubgroup(config.value, groupId, subgroupId);
    const item = (subgroup?.items || []).find((entry) => entry.id === itemId);
    if (!subgroup || !item) return;

    if (subgroup.items.length <= 1) {
      saveStatus.value = "error";
      saveError.value = "В подгруппе должен остаться хотя бы один элемент.";
      return;
    }

    if (!window.confirm(`Удалить сервис "${item.title}"?`)) return;

    await applyConfigMutation((cfg) => {
      const targetSubgroup = findSubgroup(cfg, groupId, subgroupId);
      if (!targetSubgroup) return false;

      const index = (targetSubgroup.items || []).findIndex(
        (entry) => entry.id === itemId,
      );
      if (index < 0) return false;
      targetSubgroup.items.splice(index, 1);

      if (selectedNode.itemId === itemId) {
        selectedNode.itemId = "";
      }
    });
  }

  function clearDragState() {
    dragState.type = "";
    dragState.groupId = "";
    dragState.subgroupId = "";
    dragState.itemId = "";
  }

  function onGroupDragStart(event, group) {
    if (!editMode.value) return;
    if (!isDirectGroupNode(group)) return;
    const groupId = group.id;
    dragState.type = "group";
    dragState.groupId = groupId;
    dragState.subgroupId = "";
    dragState.itemId = "";
    if (event.dataTransfer) {
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", `group:${groupId}`);
    }
  }

  function onSubgroupDragStart(event, groupId, subgroupId) {
    if (!editMode.value) return;
    dragState.type = "subgroup";
    dragState.groupId = groupId;
    dragState.subgroupId = subgroupId;
    dragState.itemId = "";
    if (event.dataTransfer) {
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", `subgroup:${subgroupId}`);
    }
  }

  function onItemDragStart(event, groupId, subgroupId, itemId) {
    if (!editMode.value) return;
    dragState.type = "item";
    dragState.groupId = groupId;
    dragState.subgroupId = subgroupId;
    dragState.itemId = itemId;
    if (event.dataTransfer) {
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", `item:${itemId}`);
    }
  }

  function onGroupDragOver(event, targetGroup) {
    if (!editMode.value) return;
    if (!isDirectGroupNode(targetGroup)) return;
    const targetGroupId = targetGroup.id;
    if (dragState.type !== "group") return;
    if (dragState.groupId === targetGroupId) return;
    event.preventDefault();
  }

  async function onGroupDrop(event, targetGroup) {
    if (!editMode.value) return;
    if (!isDirectGroupNode(targetGroup)) return;
    const targetGroupId = targetGroup.id;
    if (dragState.type !== "group") return;
    if (!dragState.groupId || dragState.groupId === targetGroupId) return;
    event.preventDefault();

    const sourceGroupId = dragState.groupId;
    clearDragState();

    await applyConfigMutation((cfg) =>
      moveGroup(cfg, sourceGroupId, targetGroupId),
    );
  }

  function onSubgroupDragOver(event, targetGroupId, targetSubgroupId) {
    if (!editMode.value) return;
    if (dragState.type === "subgroup") {
      if (dragState.subgroupId === targetSubgroupId) return;
      event.preventDefault();
      return;
    }

    if (dragState.type === "item") {
      event.preventDefault();
    }
  }

  async function onSubgroupDrop(event, targetGroupId, targetSubgroupId) {
    if (!editMode.value) return;

    if (dragState.type === "subgroup") {
      event.preventDefault();
      const sourceGroupId = dragState.groupId;
      const sourceSubgroupId = dragState.subgroupId;
      clearDragState();

      await applyConfigMutation((cfg) =>
        moveSubgroup(
          cfg,
          sourceGroupId,
          sourceSubgroupId,
          targetGroupId,
          targetSubgroupId,
        ),
      );
      return;
    }

    if (dragState.type === "item") {
      event.preventDefault();
      const sourceGroupId = dragState.groupId;
      const sourceSubgroupId = dragState.subgroupId;
      const sourceItemId = dragState.itemId;
      clearDragState();

      await applyConfigMutation((cfg) =>
        moveItemToSubgroupEnd(
          cfg,
          sourceGroupId,
          sourceSubgroupId,
          sourceItemId,
          targetGroupId,
          targetSubgroupId,
        ),
      );
    }
  }

  function onItemDragOver(
    event,
    _targetGroupId,
    _targetSubgroupId,
    targetItemId,
  ) {
    if (!editMode.value) return;
    if (dragState.type !== "item") return;
    if (dragState.itemId === targetItemId) return;
    event.preventDefault();
  }

  async function onItemDrop(
    event,
    targetGroupId,
    targetSubgroupId,
    targetItemId,
  ) {
    if (!editMode.value) return;
    if (dragState.type !== "item") return;
    if (!dragState.itemId || dragState.itemId === targetItemId) return;
    event.preventDefault();

    const sourceGroupId = dragState.groupId;
    const sourceSubgroupId = dragState.subgroupId;
    const sourceItemId = dragState.itemId;
    clearDragState();

    await applyConfigMutation((cfg) =>
      moveItemBefore(
        cfg,
        sourceGroupId,
        sourceSubgroupId,
        sourceItemId,
        targetGroupId,
        targetSubgroupId,
        targetItemId,
      ),
    );
  }

  function isWidgetBlock(block) {
    return block?.type === "widget_row" || block?.type === "widget_grid";
  }

  function resolveWidgets(widgetIds = []) {
    return widgetIds
      .map((widgetId) => widgetById.value.get(widgetId))
      .filter(Boolean);
  }

  function isLargeIndicator(widget) {
    return LARGE_INDICATOR_TYPES.has(String(widget?.type || ""));
  }

  function indicatorPreviewEntries(widget) {
    return statListEntries(widget).slice(0, 2);
  }

  function openIndicatorView(widgetId) {
    const widget = sidebarIndicators.value.find(
      (entry) => entry.id === widgetId,
    );
    if (!widget || !isLargeIndicator(widget)) return;
    activeIndicatorViewId.value = widget.id;
  }

  function selectSidebarIndicator(widget) {
    if (isLargeIndicator(widget)) {
      openIndicatorView(widget.id);
    }
  }

  function resolveBlockGroups(groupIds = []) {
    const resolved = [];

    for (const id of groupIds) {
      const group = groupById.value.get(id);
      if (group) {
        resolved.push({
          key: `group:${group.id}`,
          id: group.id,
          title: group.title,
          icon: group.icon || null,
          description: group.description || "",
          layout: group.layout || "auto",
          subgroups: group.subgroups || [],
        });
        continue;
      }

      const subgroupRef = subgroupById.value.get(id);
      if (subgroupRef) {
        resolved.push({
          key: `subgroup:${subgroupRef.subgroup.id}`,
          id: subgroupRef.group.id,
          title: subgroupRef.group.title,
          icon: subgroupRef.group.icon || null,
          description: subgroupRef.group.description || "",
          layout: subgroupRef.group.layout || "auto",
          subgroups: [subgroupRef.subgroup],
        });
      }
    }

    return resolved;
  }

  function syncTreeGroupsState() {
    const activeKeys = new Set(treeGroups.value.map((group) => group.key));

    for (const key of Object.keys(expandedGroups)) {
      if (!activeKeys.has(key)) {
        delete expandedGroups[key];
      }
    }

    for (const group of treeGroups.value) {
      if (expandedGroups[group.key] == null) {
        expandedGroups[group.key] = true;
      }
    }

    if (selectedNode.groupKey && !activeKeys.has(selectedNode.groupKey)) {
      clearSelectedNode();
    }
  }

  function clearSelectedNode() {
    selectedNode.groupKey = "";
    selectedNode.subgroupId = "";
    selectedNode.itemId = "";
  }

  function safeUrlHost(rawValue) {
    try {
      return new URL(String(rawValue || "")).hostname || "";
    } catch {
      return "";
    }
  }

  function deriveSiteLabel(item, group, tags) {
    const itemSite = String(item?.site || "").trim();
    if (itemSite) return itemSite;

    const groupSite = String(group?.site || "").trim();
    if (groupSite) return groupSite;

    const siteTag = (tags || []).find((tag) =>
      String(tag || "")
        .toLowerCase()
        .startsWith("site:"),
    );
    if (!siteTag) return "";
    return String(siteTag).slice(5).trim();
  }

  function normalizedItemTags(item) {
    return (item?.tags || [])
      .map((tag) => String(tag || "").trim())
      .filter(Boolean);
  }

  function resolveGroupByNodeKey(groupKey) {
    const key = String(groupKey || "");
    if (!key.startsWith("group:")) return null;
    return groupById.value.get(key.slice(6)) || null;
  }

  function resolveItemSite(item, group = null) {
    return deriveSiteLabel(item, group, normalizedItemTags(item));
  }

  function itemSite(item, groupKey = "") {
    const resolvedGroup = resolveGroupByNodeKey(
      item?.__originGroupKey || groupKey,
    );
    return resolveItemSite(item, resolvedGroup);
  }

  function filterGroupsBySite(groups = []) {
    if (siteFilter.value === "all") return groups;

    return groups
      .map((group) => {
        const nextSubgroups = (group.subgroups || [])
          .map((subgroup) => ({
            ...subgroup,
            items: (subgroup.items || []).filter(
              (item) =>
                resolveItemSite(item, group).toLowerCase() === siteFilter.value,
            ),
          }))
          .filter((subgroup) => subgroup.items.length > 0);

        if (!nextSubgroups.length) return null;
        return {
          ...group,
          subgroups: nextSubgroups,
        };
      })
      .filter(Boolean);
  }

  function setSiteFilter(value) {
    const normalized = String(value || "all")
      .trim()
      .toLowerCase();
    const allowed = new Set(
      siteFilterOptions.value.map((option) => option.value),
    );
    siteFilter.value = allowed.has(normalized) ? normalized : "all";
  }

  function openCommandPalette() {
    commandPaletteQuery.value = "";
    commandPaletteActiveIndex.value = 0;
    commandPaletteOpen.value = true;
  }

  function closeCommandPalette() {
    commandPaletteOpen.value = false;
    commandPaletteQuery.value = "";
    commandPaletteActiveIndex.value = 0;
  }

  function toggleCommandPalette() {
    if (commandPaletteOpen.value) {
      closeCommandPalette();
      return;
    }
    openCommandPalette();
  }

  function openSettingsPanel() {
    settingsPanel.open = true;
  }

  function closeSettingsPanel() {
    settingsPanel.open = false;
  }

  function toggleSettingsPanel() {
    settingsPanel.open = !settingsPanel.open;
  }

  function setCommandPaletteQuery(value) {
    commandPaletteQuery.value = String(value || "");
    commandPaletteActiveIndex.value = 0;
  }

  function setCommandPaletteActiveIndex(index) {
    const lastIndex = commandPaletteResults.value.length - 1;
    if (lastIndex < 0) {
      commandPaletteActiveIndex.value = 0;
      return;
    }
    commandPaletteActiveIndex.value = Math.min(Math.max(index, 0), lastIndex);
  }

  function moveCommandPaletteSelection(step) {
    const resultsCount = commandPaletteResults.value.length;
    if (!resultsCount) {
      commandPaletteActiveIndex.value = 0;
      return;
    }

    const start = commandPaletteActiveIndex.value;
    const next = (start + step + resultsCount) % resultsCount;
    commandPaletteActiveIndex.value = next;
  }

  function focusCommandPaletteEntry(entry) {
    if (!entry) return;
    if (entry.pageId) {
      activePageId.value = entry.pageId;
    }
    selectItemNode(entry.groupKey, entry.subgroupId, entry.item.id);
  }

  function activateCommandPaletteEntry(entry) {
    if (!entry) return;

    if (entry.type === "action" && entry.action === "open_settings_panel") {
      closeCommandPalette();
      openSettingsPanel();
      return;
    }

    focusCommandPaletteEntry(entry);
    openItem(entry.item);
    closeCommandPalette();
  }

  function activateCommandPaletteSelection() {
    activateCommandPaletteEntry(activeCommandPaletteEntry.value);
  }

  async function copyCommandPaletteEntryUrl(entry) {
    if (entry?.type !== "item" || !entry?.item?.url) return;
    await copyUrl(entry.item.url);
  }

  function toggleGroupNode(groupKey) {
    expandedGroups[groupKey] = !isGroupExpanded(groupKey);
    selectedNode.groupKey = groupKey;
    selectedNode.subgroupId = "";
    selectedNode.itemId = "";
  }

  function selectSubgroupNode(groupKey, subgroupId) {
    expandedGroups[groupKey] = true;
    selectedNode.groupKey = groupKey;
    selectedNode.subgroupId = subgroupId;
    selectedNode.itemId = "";
  }

  function selectItemNode(groupKey, subgroupId, itemId) {
    expandedGroups[groupKey] = true;
    selectedNode.groupKey = groupKey;
    selectedNode.subgroupId = subgroupId;
    selectedNode.itemId = itemId;
  }

  function isGroupExpanded(groupKey) {
    return Boolean(expandedGroups[groupKey]);
  }

  function isGroupSelected(groupKey) {
    return (
      selectedNode.groupKey === groupKey &&
      !selectedNode.subgroupId &&
      !selectedNode.itemId
    );
  }

  function isSubgroupSelected(groupKey, subgroupId) {
    return (
      selectedNode.groupKey === groupKey &&
      selectedNode.subgroupId === subgroupId &&
      !selectedNode.itemId
    );
  }

  function isItemSelected(itemId) {
    return selectedNode.itemId === itemId;
  }

  function filteredBlockGroups(groupIds = []) {
    const groups = resolveBlockGroups(groupIds);
    const siteFiltered = filterGroupsBySite(groups);
    const selectionFiltered = isSidebarHidden.value
      ? siteFiltered
      : filterGroupsBySelectedNode(siteFiltered);
    const regrouped = applyServiceGroupingMode(selectionFiltered);
    const visibleCount = regrouped.length;
    return regrouped.map((group) => ({
      ...group,
      __visibleCount: visibleCount,
    }));
  }

  function hasTreeSelection() {
    return Boolean(
      selectedNode.groupKey || selectedNode.subgroupId || selectedNode.itemId,
    );
  }

  function normalizeTagLabel(rawTag) {
    const normalized = String(rawTag || "").trim();
    return normalized || "Без тега";
  }

  function tagsForItem(item) {
    const uniqueTags = new Set(
      normalizedItemTags(item)
        .map((tag) => normalizeTagLabel(tag))
        .filter(Boolean),
    );
    if (!uniqueTags.size) {
      uniqueTags.add("Без тега");
    }
    return Array.from(uniqueTags);
  }

  function withOrigin(item, groupKey, subgroupId) {
    return {
      ...item,
      __originGroupKey: groupKey,
      __originSubgroupId: subgroupId,
    };
  }

  function filterGroupsBySelectedNode(groups = []) {
    if (!hasTreeSelection()) return groups;

    return groups
      .map((group) => {
        if (selectedNode.groupKey && group.key !== selectedNode.groupKey) {
          return null;
        }

        let nextSubgroups = group.subgroups || [];

        if (selectedNode.subgroupId) {
          nextSubgroups = nextSubgroups.filter(
            (subgroup) => subgroup.id === selectedNode.subgroupId,
          );
        }

        if (selectedNode.itemId) {
          nextSubgroups = nextSubgroups
            .map((subgroup) => ({
              ...subgroup,
              items: (subgroup.items || []).filter(
                (item) => item.id === selectedNode.itemId,
              ),
            }))
            .filter((subgroup) => subgroup.items.length > 0);
        }

        if (!nextSubgroups.length) return null;
        return {
          ...group,
          subgroups: nextSubgroups,
        };
      })
      .filter(Boolean);
  }

  function groupByTagsInEachGroup(groups = []) {
    return groups
      .map((group) => {
        const tagsMap = new Map();

        for (const subgroup of group.subgroups || []) {
          for (const item of subgroup.items || []) {
            for (const tag of tagsForItem(item)) {
              if (!tagsMap.has(tag)) {
                tagsMap.set(tag, []);
              }

              tagsMap.get(tag).push(withOrigin(item, group.key, subgroup.id));
            }
          }
        }

        const sortedTagEntries = Array.from(tagsMap.entries()).sort(
          ([left], [right]) =>
            left.localeCompare(right, "ru", { sensitivity: "base" }),
        );
        const tagSubgroups = sortedTagEntries.map(([tag, items]) => ({
          id: `tag-${normalizeId(`${group.id}-${tag}`, "tag")}`,
          title: `#${tag}`,
          icon: "tag",
          items,
        }));

        if (!tagSubgroups.length) return null;
        return {
          ...group,
          subgroups: tagSubgroups,
        };
      })
      .filter(Boolean);
  }

  function groupByTagsOnly(groups = []) {
    const tagsMap = new Map();

    for (const group of groups) {
      for (const subgroup of group.subgroups || []) {
        for (const item of subgroup.items || []) {
          for (const tag of tagsForItem(item)) {
            if (!tagsMap.has(tag)) {
              tagsMap.set(tag, []);
            }
            tagsMap.get(tag).push(withOrigin(item, group.key, subgroup.id));
          }
        }
      }
    }

    const sortedTagEntries = Array.from(tagsMap.entries()).sort(
      ([left], [right]) =>
        left.localeCompare(right, "ru", { sensitivity: "base" }),
    );

    return sortedTagEntries.map(([tag, items]) => {
      const tagId = normalizeId(tag, "tag");
      return {
        key: `tags:${tagId}`,
        id: `tags-${tagId}`,
        title: `#${tag}`,
        icon: "tag",
        description: "Сервисы, сгруппированные только по тегам.",
        layout: "inline",
        subgroups: [
          {
            id: `tags-${tagId}-items`,
            title: "Сервисы",
            items,
          },
        ],
      };
    });
  }

  function toFlatTileGroups(groups = []) {
    const items = [];

    for (const group of groups) {
      for (const subgroup of group.subgroups || []) {
        for (const item of subgroup.items || []) {
          items.push(withOrigin(item, group.key, subgroup.id));
        }
      }
    }

    if (!items.length) return [];
    return [
      {
        key: "flat:all",
        id: "flat-all",
        title: "Все сервисы",
        icon: "layout-grid",
        description: "Плоское отображение без группировки.",
        layout: "full",
        subgroups: [
          {
            id: "flat-all-items",
            title: "Плитка",
            items,
          },
        ],
      },
    ];
  }

  function applyServiceGroupingMode(groups = []) {
    if (isSidebarHidden.value) {
      return toFlatTileGroups(groups);
    }

    if (serviceGroupingMode.value === "tags_in_groups") {
      return groupByTagsInEachGroup(groups);
    }

    if (serviceGroupingMode.value === "tags") {
      return groupByTagsOnly(groups);
    }

    if (serviceGroupingMode.value === "flat") {
      return toFlatTileGroups(groups);
    }

    return groups;
  }

  function isInlineGroupLayout(group) {
    const mode = String(group?.layout || "auto").toLowerCase();
    if (mode === "inline") return true;
    if (mode === "full") return false;
    return Number(group?.__visibleCount || 0) > 1;
  }

  function groupTotalItems(group) {
    return (group.subgroups || []).reduce(
      (acc, subgroup) => acc + (subgroup.items || []).length,
      0,
    );
  }

  function subgroupTotalItems(subgroup) {
    return (subgroup?.items || []).length;
  }

  function groupOnlineItems(group) {
    let online = 0;
    for (const subgroup of group.subgroups || []) {
      for (const item of subgroup.items || []) {
        if (healthState(item.id)?.ok) {
          online += 1;
        }
      }
    }
    return online;
  }

  function clearItemFaviconFailures() {
    for (const key of Object.keys(itemFaviconFailures)) {
      delete itemFaviconFailures[key];
    }
  }

  function faviconOriginFromUrl(rawValue) {
    return originFromHttpUrl(rawValue);
  }

  function itemFaviconKey(item) {
    const origin = faviconOriginFromUrl(item?.url);
    if (!origin) return "";
    const itemId = String(item?.id || "");
    return `${itemId}|${origin}`;
  }

  function itemFaviconSrc(item) {
    const origin = faviconOriginFromUrl(item?.url);
    if (!origin) return "";

    const key = itemFaviconKey(item);
    if (key && itemFaviconFailures[key]) return "";
    return `${origin}/favicon.ico`;
  }

  function markItemFaviconFailed(item) {
    const key = itemFaviconKey(item);
    if (!key) return;
    itemFaviconFailures[key] = true;
  }

  function resolvePageIcon(page) {
    return resolvePageIconSemantic(page);
  }

  function resolveGroupIcon(group) {
    return resolveGroupIconSemantic(group);
  }

  function resolveSubgroupIcon(subgroup) {
    return resolveSubgroupIconSemantic(subgroup);
  }

  function resolveItemIcon(item) {
    return resolveItemIconSemantic(item);
  }

  function resolveWidgetIcon(widget) {
    return resolveWidgetIconSemantic(widget);
  }

  function widgetState(widgetId) {
    return widgetStates[widgetId] || null;
  }

  function actionKey(widgetId, actionId) {
    return `${widgetId}:${actionId}`;
  }

  function isActionBusy(widgetId, actionId) {
    return Boolean(actionBusy[actionKey(widgetId, actionId)]);
  }

  function resolveExpression(payload, expression) {
    if (!expression || typeof expression !== "string") return null;
    if (expression === "$") return payload;
    if (!expression.startsWith("$.")) return null;

    let current = payload;
    const parts = expression.slice(2).split(".");

    for (const part of parts) {
      if (current == null) return null;

      const arrayMatch = part.match(/^(.*)\[\*\]$/);
      if (arrayMatch) {
        const key = arrayMatch[1];
        const value = key ? current?.[key] : current;
        return Array.isArray(value) ? value : [];
      }

      current = current?.[part];
    }

    return current;
  }

  function statCardValue(widget) {
    const payload = widgetState(widget.id)?.payload;
    const value = resolveExpression(payload, widget.data?.mapping?.value);
    return value ?? "—";
  }

  function statCardSubtitle(widget) {
    const payload = widgetState(widget.id)?.payload;
    const subtitle = resolveExpression(payload, widget.data?.mapping?.subtitle);
    return subtitle ?? "";
  }

  function statCardTrend(widget) {
    const payload = widgetState(widget.id)?.payload;
    const trend = resolveExpression(payload, widget.data?.mapping?.trend);
    return trend ?? "";
  }

  function statListEntries(widget) {
    const payload = widgetState(widget.id)?.payload;
    const mapping = widget.data?.mapping || {};
    const items = resolveExpression(payload, mapping.items);

    if (!Array.isArray(items)) return [];

    return items.map((entry) => {
      const title = resolveExpression(entry, mapping.item_title) ?? "-";
      const value = resolveExpression(entry, mapping.item_value) ?? "-";
      return { title, value };
    });
  }

  function tableRows(widget) {
    const payload = widgetState(widget.id)?.payload;
    const rowsExpression = widget.data?.mapping?.rows;
    const fromExpression = resolveExpression(payload, rowsExpression);

    if (Array.isArray(fromExpression)) return fromExpression;
    if (Array.isArray(payload)) return payload;
    if (Array.isArray(payload?.items)) return payload.items;
    return [];
  }

  function normalizeEndpoint(endpoint) {
    if (!endpoint) return "";
    if (endpoint.startsWith("http://") || endpoint.startsWith("https://"))
      return endpoint;
    if (endpoint.startsWith("/")) return endpoint;
    return `/${endpoint}`;
  }

  function resetWidgetPolling() {
    for (const timer of widgetIntervals.values()) {
      clearInterval(timer);
    }
    widgetIntervals.clear();
  }

  function stopHealthPolling() {
    if (healthPollTimer) {
      clearTimeout(healthPollTimer);
      healthPollTimer = 0;
    }
    if (healthStreamReconnectTimer) {
      clearTimeout(healthStreamReconnectTimer);
      healthStreamReconnectTimer = 0;
    }
    if (healthStream) {
      healthStream.close();
      healthStream = null;
    }
  }

  function healthState(itemId) {
    return healthStates[itemId] || null;
  }

  function isHealthDegraded(state) {
    return Boolean(
      state?.ok &&
        state.latency_ms != null &&
        state.latency_ms >= DEGRADED_LATENCY_MS,
    );
  }

  function resolvedHealthLevel(state) {
    if (!state) return "unknown";

    const level = String(state.level || "").toLowerCase();
    if (
      ["online", "degraded", "down", "unknown", "indirect_failure"].includes(
        level,
      )
    ) {
      return level;
    }

    if (isHealthDegraded(state)) return "degraded";
    return state.ok ? "online" : "down";
  }

  function healthClass(itemId) {
    const state = healthState(itemId);
    const level = resolvedHealthLevel(state);

    if (level === "online") return "ok";
    if (level === "degraded") return "degraded";
    if (level === "down" || level === "indirect_failure") return "down";
    return "unknown";
  }

  function healthLabel(itemId) {
    const state = healthState(itemId);
    if (!state) return "Проверка...";
    const level = resolvedHealthLevel(state);

    if (level === "online") {
      if (state.latency_ms != null) {
        return `Online • ${state.latency_ms} ms`;
      }
      return "Online";
    }

    if (level === "degraded") {
      if (state.latency_ms != null) {
        return `Degraded • ${state.latency_ms} ms`;
      }
      if (state.status_code != null) {
        return `Degraded • HTTP ${state.status_code}`;
      }
      if (state.error) {
        return `Degraded • ${state.error}`;
      }
      if (state.reason) {
        return `Degraded • ${String(state.reason).replaceAll("_", " ")}`;
      }
      return "Degraded";
    }

    if (level === "indirect_failure") {
      return "Indirect failure";
    }

    if (level === "down") {
      if (state.error) {
        return `Offline • ${state.error}`;
      }

      if (state.status_code != null) {
        return `Offline • HTTP ${state.status_code}`;
      }

      return "Offline";
    }

    return "Unknown";
  }

  function applyHealthPayload(payload, ids = []) {
    const incomingById = new Map();
    for (const itemStatus of payload?.items || []) {
      const status =
        itemStatus && typeof itemStatus === "object" ? itemStatus : null;
      const statusItemId = String(status?.item_id || "").trim();
      if (!statusItemId) continue;
      incomingById.set(statusItemId, status);
      healthStates[statusItemId] = status;
    }

    for (const id of ids) {
      const normalizedId = String(id || "").trim();
      if (!normalizedId || incomingById.has(normalizedId)) continue;
      if (!healthStates[normalizedId]) {
        healthStates[normalizedId] = {
          item_id: normalizedId,
          ok: false,
          checked_url: "",
          status_code: null,
          latency_ms: null,
          error: "healthcheck unavailable",
        };
      }
    }
  }

  function startHealthStreaming() {
    const stream = createDashboardHealthStream();
    if (!stream) return false;

    healthStream = stream;
    const fallbackIds = visibleTreeItemIds.value;

    const handleSnapshot = (event) => {
      if (!event?.data) return;
      try {
        const payload = JSON.parse(event.data);
        applyHealthPayload(payload, fallbackIds);
      } catch {
        // Ignore malformed stream events and keep connection alive.
      }
    };

    stream.addEventListener("snapshot", handleSnapshot);
    stream.onmessage = handleSnapshot;
    stream.onerror = () => {
      if (healthStream !== stream) return;
      stream.close();
      healthStream = null;

      if (!isDocumentVisible.value) return;
      healthStreamReconnectTimer = window.setTimeout(async () => {
        healthStreamReconnectTimer = 0;
        if (!startHealthStreaming()) {
          await refreshHealth();
          scheduleNextHealthPoll();
        }
      }, HEALTH_STREAM_RECONNECT_MS);
    };

    return true;
  }

  async function refreshHealth(itemIds = null) {
    if (!Array.isArray(itemIds) && !isDocumentVisible.value) return;

    const sourceIds =
      Array.isArray(itemIds) && itemIds.length
        ? itemIds
        : visibleTreeItemIds.value;
    const ids = Array.from(
      new Set(
        sourceIds.map((value) => String(value || "").trim()).filter(Boolean),
      ),
    );
    if (!ids.length) return;

    try {
      const payload = await fetchDashboardHealth(ids);
      applyHealthPayload(payload, ids);
    } catch {
      applyHealthPayload({ items: [] }, ids);
    }
  }

  async function startHealthPolling() {
    stopHealthPolling();
    if (startHealthStreaming()) {
      return;
    }

    await refreshHealth();
    scheduleNextHealthPoll();
  }

  function nextHealthPollDelayMs() {
    let hasDown = false;
    let hasDegraded = false;

    for (const itemId of visibleTreeItemIds.value) {
      const level = resolvedHealthLevel(healthState(itemId));
      if (level === "down" || level === "indirect_failure") {
        hasDown = true;
        break;
      }
      if (level === "degraded") {
        hasDegraded = true;
      }
    }

    if (hasDown) return HEALTH_REFRESH_DOWN_MS;
    if (hasDegraded) return HEALTH_REFRESH_DEGRADED_MS;
    return HEALTH_REFRESH_MS;
  }

  function scheduleNextHealthPoll() {
    stopHealthPolling();
    if (!isDocumentVisible.value) return;

    const delayMs = nextHealthPollDelayMs();
    healthPollTimer = window.setTimeout(async () => {
      await refreshHealth();
      scheduleNextHealthPoll();
    }, delayMs);
  }

  async function refreshWidget(widgetId) {
    const widget = widgetById.value.get(widgetId);
    if (!widget) return;

    const endpoint = normalizeEndpoint(widget.data?.endpoint);
    if (!endpoint) return;

    if (!widgetStates[widgetId]) {
      widgetStates[widgetId] = {
        loading: false,
        error: "",
        payload: null,
        lastUpdated: 0,
      };
    }

    const state = widgetStates[widgetId];
    state.loading = true;
    state.error = "";

    try {
      state.payload = await requestJson(endpoint);
      state.lastUpdated = Date.now();
    } catch (error) {
      state.error = error?.message || "Ошибка загрузки виджета";
    } finally {
      state.loading = false;
    }
  }

  async function initWidgetPolling() {
    resetWidgetPolling();

    const initialLoads = [];

    for (const widget of widgets.value) {
      initialLoads.push(refreshWidget(widget.id));

      if (!normalizeEndpoint(widget.data?.endpoint)) continue;
      const intervalMs =
        Math.max(1, Number(widget.data?.refresh_sec || 0)) * 1000;

      const timer = window.setInterval(() => {
        refreshWidget(widget.id);
      }, intervalMs);

      widgetIntervals.set(widget.id, timer);
    }

    await Promise.all(initialLoads);
  }

  async function runWidgetAction(widgetId, action) {
    const key = actionKey(widgetId, action.id);
    const endpoint = normalizeEndpoint(action.endpoint);
    if (!endpoint) return;

    actionBusy[key] = true;

    try {
      await requestJson(endpoint, {
        method: String(action.method || "GET").toUpperCase(),
      });
      await refreshWidget(widgetId);
    } catch (error) {
      if (!widgetStates[widgetId]) {
        widgetStates[widgetId] = {
          loading: false,
          error: "",
          payload: null,
          lastUpdated: 0,
        };
      }
      widgetStates[widgetId].error =
        error?.message || "Не удалось выполнить действие";
    } finally {
      actionBusy[key] = false;
    }
  }

  async function loadConfig() {
    loadingConfig.value = true;
    configError.value = "";
    saveStatus.value = "idle";
    saveError.value = "";
    clearItemFaviconFailures();

    try {
      const data = await fetchDashboardConfig();
      config.value = data;

      if (
        !activePageId.value ||
        !pages.value.some((page) => page.id === activePageId.value)
      ) {
        activePageId.value = pages.value[0]?.id || "";
      }

      syncTreeGroupsState();
      applyTheme(data?.ui?.theme);
      applyGrid(data?.ui?.grid);
      await initWidgetPolling();
      await startHealthPolling();
      if (!isDocumentVisible.value) {
        pauseBackgroundPolling();
      }
    } catch (error) {
      configError.value =
        error?.message || "Не удалось загрузить dashboard-конфигурацию";
      config.value = null;
      resetWidgetPolling();
      stopHealthPolling();
    } finally {
      loadingConfig.value = false;
    }
  }

  async function openIframeItem(item) {
    const defaultSandbox = Boolean(
      config.value?.security?.iframe?.default_sandbox ?? true,
    );
    const sandboxValue = item?.iframe?.sandbox;

    iframeModal.open = true;
    iframeModal.title = item.title;
    iframeModal.src = "";
    iframeModal.error = "";
    iframeModal.loading = true;
    iframeModal.sandbox =
      sandboxValue == null ? defaultSandbox : Boolean(sandboxValue);
    iframeModal.allow = Array.isArray(item?.iframe?.allow)
      ? item.iframe.allow.join("; ")
      : "";
    iframeModal.referrerPolicy = item?.iframe?.referrer_policy || "";

    try {
      const source = await fetchIframeSource(item.id);
      iframeModal.src = source.src;
    } catch (error) {
      iframeModal.error = error?.message || "Не удалось подготовить iframe";
    } finally {
      iframeModal.loading = false;
    }
  }

  function closeIframeModal() {
    iframeModal.open = false;
    iframeModal.title = "";
    iframeModal.src = "";
    iframeModal.error = "";
    iframeModal.loading = false;
    iframeModal.sandbox = false;
    iframeModal.allow = "";
    iframeModal.referrerPolicy = "";
  }

  function openLinkItem(item) {
    if (item.open === "same_tab") {
      window.location.assign(item.url);
      return;
    }
    window.open(item.url, "_blank", "noopener,noreferrer");
  }

  function openItemInNewTab(item) {
    if (!item?.url) return;
    window.open(item.url, "_blank", "noopener,noreferrer");
  }

  function openItem(item) {
    if (item.type === "iframe") {
      openIframeItem(item);
      return;
    }

    openLinkItem(item);
  }

  function itemIp(itemId) {
    return itemIpById.value.get(String(itemId || "")) || "";
  }

  async function copyText(value) {
    const text = String(value || "");
    if (!text) return;
    if (!navigator.clipboard?.writeText) return;

    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // ignore clipboard errors
    }
  }

  async function copyUrl(url) {
    await copyText(url);
  }

  async function copyItemIp(itemId) {
    const ip = itemIp(itemId);
    if (!ip) return;
    await copyText(ip);
  }

  async function copyItemSshShortcut(itemId) {
    const ip = itemIp(itemId);
    if (!ip) return;
    await copyText(`ssh ${ip}`);
  }

  async function recheckItem(itemId) {
    if (!itemId) return;
    await refreshHealth([itemId]);
  }

  function formatLanMoment(value) {
    if (!value) return "—";
    const timestamp = new Date(value);
    if (Number.isNaN(timestamp.getTime())) return "—";
    return timestamp.toLocaleString("ru-RU", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  }

  function formatLanDuration(durationMs) {
    const value = Number(durationMs || 0);
    if (!Number.isFinite(value) || value <= 0) return "—";
    if (value < 1000) return `${Math.round(value)} ms`;
    return `${(value / 1000).toFixed(2)} s`;
  }

  function openLanHostModal(host) {
    if (!host) return;
    lanHostModal.host = host;
    lanHostModal.open = true;
  }

  function closeLanHostModal() {
    lanHostModal.open = false;
    lanHostModal.host = null;
  }

  function lanPortsLabel(host) {
    const ports = host?.open_ports || [];
    if (!ports.length) return "—";
    return ports
      .map((entry) =>
        entry?.service ? `${entry.port} (${entry.service})` : `${entry.port}`,
      )
      .join(", ");
  }

  function formatLanHttpStatus(endpoint) {
    if (!endpoint) return "—";
    if (endpoint.error) return endpoint.error;
    if (endpoint.status_code == null) return "—";
    return `HTTP ${endpoint.status_code}`;
  }

  async function refreshLanScanState({ silent = false } = {}) {
    if (lanScanRefreshInFlight) return;
    lanScanRefreshInFlight = true;

    if (!silent) {
      lanScanLoading.value = true;
    }

    try {
      lanScanState.value = await fetchLanScanState();
      lanScanError.value = "";
    } catch (error) {
      lanScanError.value =
        error?.message || "Не удалось загрузить состояние сканера LAN";
    } finally {
      lanScanRefreshInFlight = false;
      if (!silent) {
        lanScanLoading.value = false;
      }
    }
  }

  function stopLanScanPolling() {
    if (!lanScanPollTimer) return;
    window.clearInterval(lanScanPollTimer);
    lanScanPollTimer = 0;
  }

  function startLanScanPolling() {
    stopLanScanPolling();
    lanScanPollTimer = window.setInterval(() => {
      refreshLanScanState({ silent: true });
    }, LAN_SCAN_POLL_MS);
  }

  function pauseBackgroundPolling() {
    stopHealthPolling();
    stopLanScanPolling();
    resetWidgetPolling();
  }

  async function resumeBackgroundPolling() {
    if (!config.value || loadingConfig.value) return;
    await initWidgetPolling();
    await startHealthPolling();

    if (isLanPage.value) {
      await refreshLanScanState({ silent: true });
      startLanScanPolling();
    }
  }

  async function syncPollingWithVisibility() {
    if (visibilitySyncInFlight) return;
    visibilitySyncInFlight = true;

    try {
      if (isDocumentVisible.value) {
        await resumeBackgroundPolling();
      } else {
        pauseBackgroundPolling();
      }
    } finally {
      visibilitySyncInFlight = false;
    }
  }

  function handleDocumentVisibilityChange() {
    isDocumentVisible.value = document.visibilityState !== "hidden";
    syncPollingWithVisibility();
  }

  async function runLanScanNow() {
    if (lanScanActionBusy.value) return;
    lanScanActionBusy.value = true;

    try {
      const payload = await triggerLanScan();
      lanScanState.value = payload?.state || lanScanState.value;
      lanScanError.value =
        payload?.accepted || payload?.state?.queued
          ? ""
          : payload?.message || "";
    } catch (error) {
      lanScanError.value =
        error?.message || "Не удалось запустить сканирование LAN";
    } finally {
      lanScanActionBusy.value = false;
      refreshLanScanState({ silent: true });
    }
  }

  function fxMode() {
    return document.documentElement?.dataset?.fxMode || "full";
  }

  function applyMotionBudgetProfile(itemCount) {
    const root = document.documentElement;
    let budget = "high";
    let scalar = "1";

    if (itemCount >= 120) {
      budget = "low";
      scalar = "0.42";
    } else if (itemCount >= 70) {
      budget = "medium";
      scalar = "0.68";
    }

    root.dataset.motionBudget = budget;
    root.style.setProperty("--motion-budget", scalar);
  }

  function tuneParticlesConfig(config) {
    const mode = fxMode();
    if (mode === "off") return null;

    const tuned = JSON.parse(JSON.stringify(config));
    tuned.fps_limit = mode === "lite" ? 34 : 58;
    if (mode !== "lite") return tuned;

    tuned.particles.number.value = Math.max(
      24,
      Math.round(tuned.particles.number.value * 0.56),
    );
    tuned.particles.opacity.value = Number(
      (tuned.particles.opacity.value * 0.72).toFixed(2),
    );
    tuned.particles.move.speed = Number(
      (tuned.particles.move.speed * 0.74).toFixed(2),
    );
    tuned.particles.line_linked.opacity = Number(
      (tuned.particles.line_linked.opacity * 0.56).toFixed(2),
    );
    tuned.particles.line_linked.distance = Math.max(
      80,
      Math.round(tuned.particles.line_linked.distance * 0.84),
    );
    tuned.retina_detect = false;
    return tuned;
  }

  function resetParticlesContainer(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = "";
    delete container.dataset.particlesReady;
  }

  function resetAllParticlesContainers() {
    resetParticlesContainer(SIDEBAR_PARTICLES_ID);
    resetParticlesContainer(HERO_TITLE_PARTICLES_ID);
    resetParticlesContainer(HERO_CONTROLS_PARTICLES_ID);
  }

  async function reinitializeParticlesByFxMode() {
    if (particlesReinitRaf) {
      window.cancelAnimationFrame(particlesReinitRaf);
      particlesReinitRaf = 0;
    }

    particlesReinitRaf = window.requestAnimationFrame(async () => {
      particlesReinitRaf = 0;
      resetAllParticlesContainers();
      await initSidebarParticles();
      await initHeroParticles();
    });
  }

  function handleFxModeChange() {
    reinitializeParticlesByFxMode();
  }

  async function initParticles(containerId, baseConfig) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const config = tuneParticlesConfig(baseConfig);
    if (!config) {
      container.innerHTML = "";
      delete container.dataset.particlesReady;
      return;
    }

    if (container.dataset.particlesReady === "1") return;
    const isParticlesReady = await ensureParticlesJs();
    if (!isParticlesReady || !window.particlesJS) return;
    if (!document.getElementById(containerId)) return;
    if (container.dataset.particlesReady === "1") return;

    container.innerHTML = "";
    window.particlesJS(containerId, config);
    container.dataset.particlesReady = "1";
  }

  async function initSidebarParticles() {
    await initParticles(SIDEBAR_PARTICLES_ID, SIDEBAR_PARTICLES_CONFIG);
  }

  async function initHeroParticles() {
    await Promise.all([
      initParticles(HERO_TITLE_PARTICLES_ID, HERO_PARTICLES_CONFIG),
      initParticles(HERO_CONTROLS_PARTICLES_ID, HERO_PARTICLES_CONFIG),
    ]);
  }

  let hasInitializedActivePage = false;

  watch(
    () => activePage.value?.id,
    async () => {
      if (hasInitializedActivePage) {
        activeIndicatorViewId.value = "";
        treeFilter.value = "";
        clearSelectedNode();
      } else {
        hasInitializedActivePage = true;
      }
      syncTreeGroupsState();
      refreshHealth();
      await nextTick();
      await initHeroParticles();
    },
  );

  watch(
    () => activeIndicatorWidget.value?.id,
    async () => {
      await nextTick();
      await initHeroParticles();
    },
  );

  watch(
    () => activePageWidgetIds.value,
    (widgetIds) => {
      if (
        activeIndicatorViewId.value &&
        !widgetIds.includes(activeIndicatorViewId.value)
      ) {
        activeIndicatorViewId.value = "";
      }
    },
    { deep: true },
  );

  watch(
    () => treeGroups.value,
    () => {
      syncTreeGroupsState();
      refreshHealth();
    },
    { deep: true },
  );

  watch(
    () => commandPaletteResults.value.length,
    (length) => {
      if (!length) {
        commandPaletteActiveIndex.value = 0;
        return;
      }

      if (commandPaletteActiveIndex.value >= length) {
        commandPaletteActiveIndex.value = length - 1;
      }
    },
  );

  watch(
    () => siteFilterOptions.value.map((option) => option.value).join("|"),
    () => {
      if (
        !siteFilterOptions.value.some(
          (option) => option.value === siteFilter.value,
        )
      ) {
        siteFilter.value = "all";
      }
    },
  );

  watch(
    () => isLanPage.value,
    (active) => {
      if (active) {
        if (isDocumentVisible.value) {
          refreshLanScanState();
          startLanScanPolling();
        }
        return;
      }
      closeLanHostModal();
      stopLanScanPolling();
    },
  );

  watch(
    () => visibleTreeItemIds.value.length,
    (count) => {
      applyMotionBudgetProfile(count);
    },
    { immediate: true },
  );

  watch(
    () => ({
      activePageId: activePageId.value,
      treeFilter: treeFilter.value,
      activeIndicatorViewId: activeIndicatorViewId.value,
      statsExpanded: statsExpanded.value,
      editMode: editMode.value,
      serviceCardView: serviceCardView.value,
      serviceGroupingMode: serviceGroupingMode.value,
      siteFilter: siteFilter.value,
      sidebarView: sidebarView.value,
      settingsPanelOpen: settingsPanel.open,
      selectedNode: {
        groupKey: selectedNode.groupKey,
        subgroupId: selectedNode.subgroupId,
        itemId: selectedNode.itemId,
      },
      expandedGroups: { ...expandedGroups },
    }),
    (snapshot) => {
      savePersistedUiState(snapshot);
    },
    { deep: true },
  );

  onMounted(async () => {
    window.addEventListener("visibilitychange", handleDocumentVisibilityChange);
    window.addEventListener("oko:fx-mode-change", handleFxModeChange);
    await initSidebarParticles();
    await loadConfig();
    await nextTick();
    await initHeroParticles();
  });

  onBeforeUnmount(() => {
    resetWidgetPolling();
    stopHealthPolling();
    stopLanScanPolling();
    closeLanHostModal();
    window.removeEventListener(
      "visibilitychange",
      handleDocumentVisibilityChange,
    );
    window.removeEventListener("oko:fx-mode-change", handleFxModeChange);
    if (particlesReinitRaf) {
      window.cancelAnimationFrame(particlesReinitRaf);
      particlesReinitRaf = 0;
    }
    if (saveStatusTimer) {
      clearTimeout(saveStatusTimer);
      saveStatusTimer = 0;
    }
    delete document.documentElement.dataset.motionBudget;
    document.documentElement.style.removeProperty("--motion-budget");

    dashboardStore = null;
  });

  dashboardStore = {
    BRAND_ICON_BY_KEY,
    DEFAULT_ITEM_URL,
    EMBLEM_SRC,
    HEALTH_REFRESH_MS,
    HERO_CONTROLS_PARTICLES_ID,
    HERO_PARTICLES_CONFIG,
    HERO_TITLE_PARTICLES_ID,
    ICON_BY_KEY,
    ICON_RULES,
    LAN_PAGE_ID,
    LAN_SCAN_POLL_MS,
    LARGE_INDICATOR_TYPES,
    SIDEBAR_PARTICLES_CONFIG,
    SIDEBAR_PARTICLES_ID,
    actionBusy,
    actionKey,
    activeCommandPaletteEntry,
    activeIndicatorViewId,
    activeIndicatorWidget,
    activePage,
    activePageGroupBlocks,
    activePageId,
    activePageWidgetIds,
    addGroup,
    addItem,
    addSubgroup,
    allItemIds,
    allSubgroupIds,
    appTagline,
    appTitle,
    applyConfigMutation,
    applyGrid,
    applyTheme,
    authProfileOptions,
    buildDefaultItem,
    buildItemFromEditorForm,
    clampNumber,
    clearDragState,
    clearItemFaviconFailures,
    clearSelectedNode,
    cloneConfig,
    closeIframeModal,
    closeItemEditor,
    closeLanHostModal,
    closeCommandPalette,
    closeSettingsPanel,
    commandPaletteActiveIndex,
    commandPaletteOpen,
    commandPaletteQuery,
    commandPaletteResults,
    config,
    configError,
    copyItemIp,
    copyItemSshShortcut,
    copyCommandPaletteEntryUrl,
    copyUrl,
    createBrandIcon,
    defaultItemEditorForm,
    dragState,
    editGroup,
    editItem,
    editMode,
    editSubgroup,
    ensureAbsoluteUrl,
    ensurePageGroupsReference,
    expandedGroups,
    faviconOriginFromUrl,
    filteredBlockGroups,
    filteredTreeGroups,
    findGroup,
    findSubgroup,
    formatLanDuration,
    formatLanHttpStatus,
    formatLanMoment,
    fromToken,
    groupById,
    groupOnlineItems,
    groupTotalItems,
    healthClass,
    healthLabel,
    healthPollTimer,
    healthState,
    healthStates,
    iframeModal,
    indicatorPreviewEntries,
    initHeroParticles,
    initParticles,
    initSidebarParticles,
    initWidgetPolling,
    isActionBusy,
    isDirectGroupNode,
    isGroupExpanded,
    isGroupSelected,
    isIconCardView,
    isSidebarDetailed,
    isSidebarHidden,
    isTileCardView,
    isCompactServiceCardView,
    isInlineGroupLayout,
    isItemSelected,
    isLanPage,
    isLargeIndicator,
    isSidebarIconActive,
    isSidebarIconOnly,
    isSubgroupSelected,
    isWidgetBlock,
    itemEditor,
    itemFaviconFailures,
    itemFaviconKey,
    itemFaviconSrc,
    itemIp,
    itemSite,
    lanCidrsLabel,
    lanHostModal,
    lanHosts,
    lanPortsLabel,
    lanScanActionBusy,
    lanScanError,
    lanScanLoading,
    lanScanPollTimer,
    lanScanRefreshInFlight,
    lanScanState,
    loadConfig,
    loadingConfig,
    makeUniqueId,
    markItemFaviconFailed,
    moveGroup,
    moveCommandPaletteSelection,
    moveItemBefore,
    moveItemToSubgroupEnd,
    moveSubgroup,
    normalizeEndpoint,
    normalizeIconToken,
    normalizeId,
    normalizeLayoutBlocks,
    normalizeStringList,
    onGroupDragOver,
    onGroupDragStart,
    onGroupDrop,
    onItemCardClick,
    onItemDragOver,
    onItemDragStart,
    onItemDrop,
    onSubgroupDragOver,
    onSubgroupDragStart,
    onSubgroupDrop,
    activateCommandPaletteEntry,
    activateCommandPaletteSelection,
    openCommandPalette,
    openSettingsPanel,
    openCreateItemEditor,
    openEditItemEditor,
    openIframeItem,
    openIndicatorView,
    openItem,
    openItemInNewTab,
    openLanHostModal,
    openLinkItem,
    pageHealthSummary,
    pages,
    persistConfig,
    pickSemanticIcon,
    refreshHealth,
    recheckItem,
    refreshLanScanState,
    refreshWidget,
    removeGroup,
    removeItem,
    removeSubgroup,
    resetWidgetPolling,
    resolveBlockGroups,
    resolveExpression,
    resolveGroupIcon,
    resolveItemIcon,
    resolvePageIcon,
    resolveSubgroupIcon,
    resolveWidgetIcon,
    resolveWidgets,
    runLanScanNow,
    runWidgetAction,
    saveError,
    saveStatus,
    saveStatusLabel,
    saveStatusTimer,
    setCommandPaletteActiveIndex,
    setCommandPaletteQuery,
    setSiteFilter,
    settingsPanel,
    sidebarViewToggleTitle,
    selectItemNode,
    selectSidebarIconNode,
    selectSidebarIndicator,
    selectSubgroupNode,
    selectedNode,
    serviceCardView,
    siteFilter,
    siteFilterOptions,
    serviceGroupingMode,
    serviceGroupingOptions,
    servicePresentationOptions,
    sidebarIconNodeTitle,
    sidebarIconNodes,
    sidebarIndicatorSummary,
    sidebarIndicators,
    sidebarView,
    startHealthPolling,
    startLanScanPolling,
    statCardSubtitle,
    statCardTrend,
    statCardValue,
    statListEntries,
    statsExpanded,
    stopHealthPolling,
    stopLanScanPolling,
    subgroupById,
    subgroupTotalItems,
    submitItemEditor,
    syncTreeGroupsState,
    tableRows,
    toggleCommandPalette,
    toggleEditMode,
    toggleGroupNode,
    toggleSettingsPanel,
    toggleServiceCardView,
    toggleSidebarView,
    treeFilter,
    treeGroups,
    visibleTreeItemIds,
    widgetById,
    widgetIntervals,
    widgetState,
    widgetStates,
    widgets,
  };

  return dashboardStore;
}
