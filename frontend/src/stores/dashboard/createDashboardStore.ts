import {
  computed,
  onBeforeUnmount,
  onMounted,
  reactive,
  ref,
  watch,
} from "vue";
import {
  fetchDashboardConfig,
  requestJson,
  updateDashboardConfig,
} from "@/services/dashboardApi";
import { resolveRequestUrl } from "@/services/requestJson";
import {
  connectOkoSseStream,
  type OkoSseStream,
} from "@/services/eventStream";
import { EVENT_FX_MODE_CHANGE, onOkoEvent } from "@/services/events";
import { ensureParticlesJs } from "@/services/particlesLoader";
import { goPluginsPanel, goSettings } from "@/core/navigation/nav";
import {
  BRAND_ICON_BY_KEY,
  createBrandIcon,
} from "@/stores/dashboard/icons/brandIcons";
import { ICON_BY_KEY, ICON_RULES } from "@/stores/dashboard/icons/keywordIcons";
import {
  fromToken,
  normalizeIconToken,
  pickSemanticIcon,
  resolveGroupIcon as resolveGroupIconSemantic,
  resolveItemIcon as resolveItemIconSemantic,
  resolvePageIcon as resolvePageIconSemantic,
  resolveSubgroupIcon as resolveSubgroupIconSemantic,
  resolveWidgetIcon as resolveWidgetIconSemantic,
} from "@/stores/dashboard/icons/semanticResolver";
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
} from "@/stores/dashboard/configTreeUtils";
import {
  COMMAND_PALETTE_EMPTY_LIMIT,
  COMMAND_PALETTE_LIMIT,
  DEFAULT_ITEM_URL,
  DEGRADED_LATENCY_MS,
  EMBLEM_SRC,
  EVENTS_STREAM_PATH,
  EVENT_STREAM_RECONNECT_MS,
  LARGE_INDICATOR_TYPES,
  SERVICE_CARD_VIEW_VALUES,
  SERVICE_GROUPING_OPTIONS,
  SERVICE_GROUPING_VALUES,
  SERVICE_PRESENTATION_OPTIONS,
  SIDEBAR_PARTICLES_CONFIG,
  SIDEBAR_PARTICLES_ID,
  SIDEBAR_VIEW_SEQUENCE,
  UI_STATE_STORAGE_KEY,
} from "@/stores/dashboard/storeConstants";
import {
  allItemIdsInConfig,
  allSubgroupIdsInConfig,
  ensurePageGroupsReferenceInConfig,
  errorMessage,
  findGroupInConfig,
  findSubgroupInConfig,
  moveGroupInConfig,
  moveItemBeforeInConfig,
  moveItemToSubgroupEndInConfig,
  moveSubgroupInConfig,
  normalizeLayoutBlocksInConfig,
} from "@/stores/dashboard/storeConfigOps";
import {
  loadPersistedUiState,
  savePersistedUiState,
} from "@/stores/dashboard/storeUiPersistence";
import { createDashboardCrudSection } from "@/stores/dashboard/storeCrudSection";
import { createDashboardCommandPaletteSection } from "@/stores/dashboard/sections/commandPaletteSection";
import { createDashboardConfigLoadSection } from "@/stores/dashboard/sections/configLoadSection";
import { createDashboardConfigMutationSection } from "@/stores/dashboard/sections/configMutationSection";
import { createDashboardCreateEntitySection } from "@/stores/dashboard/sections/createEntitySection";
import { createDashboardFxSection } from "@/stores/dashboard/sections/fxSection";
import { createDashboardGroupingSection } from "@/stores/dashboard/sections/groupingSection";
import { createDashboardHealthSection } from "@/stores/dashboard/sections/healthSection";
import { createDashboardIconsSection } from "@/stores/dashboard/sections/iconsSection";
import { createDashboardIndicatorsSection } from "@/stores/dashboard/sections/indicatorsSection";
import { createDashboardItemActionsSection } from "@/stores/dashboard/sections/itemActionsSection";
import { createDashboardTreeDataSection } from "@/stores/dashboard/sections/treeDataSection";
import { createDashboardTreeSelectionSection } from "@/stores/dashboard/sections/treeSelectionSection";
import { createDashboardUiStyleSection } from "@/stores/dashboard/sections/uiStyleSection";
import { createDashboardWidgetRuntimeSection } from "@/stores/dashboard/sections/widgetRuntimeSection";
import { ensureAbsoluteHttpUrl, originFromHttpUrl } from "@/stores/dashboard/urlUtils";
import type {
  AuthProfile,
  CommandPaletteEntry,
  CreateChooserState,
  CreateEntityForm,
  CreateEntityKind,
  CreateEntityState,
  CreateOption,
  DashboardConfig,
  DashboardGrid,
  DashboardGroup,
  DashboardHealthPayload,
  DashboardHealthState,
  DashboardItem,
  DashboardItemHealthcheck,
  DashboardLayoutBlock,
  DashboardLayoutPage,
  DashboardSubgroup,
  DashboardTheme,
  DashboardWidget,
  DashboardWidgetAction,
  DashboardWidgetColumn,
  DashboardWidgetData,
  DashboardWidgetMapping,
  DashboardWidgetResolved,
  DragState,
  HealthLevel,
  IconEntity,
  IframeModalState,
  IframeReferrerPolicy,
  ItemEditorForm,
  ItemEditorMode,
  ItemEditorState,
  ItemOpenMode,
  ItemType,
  ItemWithOrigin,
  ParticlesConfig,
  SaveStatus,
  SelectedNodeState,
  ServiceCardView,
  ServiceGroupingMode,
  SidebarIconNode,
  SidebarViewMode,
  TreeGroupNode,
  WidgetRuntimeState,
  WidgetStatListEntry,
} from "@/stores/dashboard/storeTypes";

interface CreateDashboardStoreOptions {
  onDispose?: () => void;
}

export function createDashboardStore(
  options: CreateDashboardStoreOptions = {},
) {
  function defaultItemEditorForm(): ItemEditorForm {
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
      healthcheckTlsVerify: true,
      iframeSandboxMode: "default",
      iframeSandboxExtraTokens: [],
      iframeAllow: [],
      iframeReferrerPolicy: "",
      authProfile: "",
      parentGroupId: "",
      parentSubgroupId: "",
    };
  }

  function defaultCreateEntityForm(): CreateEntityForm {
    return {
      kind: "group",
      title: "",
      id: "",
      icon: "",
      description: "",
      parentDashboardId: "",
      parentGroupId: "",
      parentSubgroupId: "",
    };
  }

  const config = ref<DashboardConfig | null>(null);
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
  const serviceCardView = ref<ServiceCardView>("detailed");
  const serviceGroupingMode = ref<ServiceGroupingMode>("groups");
  const siteFilter = ref("all");
  const sidebarView = ref<SidebarViewMode>("detailed");
  const saveStatus = ref<SaveStatus>("idle");
  const saveError = ref("");
  const commandPaletteOpen = ref(false);
  const commandPaletteQuery = ref("");
  const commandPaletteActiveIndex = ref(0);
  const settingsPanel = reactive<{ open: boolean }>({
    open: false,
  });

  const widgetStates = reactive<Record<string, WidgetRuntimeState>>({});
  const actionBusy = reactive<Record<string, boolean>>({});
  const widgetIntervals = new Map<string, number>();
  let healthStream: OkoSseStream | null = null;
  let healthStreamReconnectTimer = 0;
  let saveStatusTimer = 0;
  let visibilitySyncInFlight = false;
  let particlesReinitRaf = 0;
  let preserveTreeSelectionOnPageSwitch = false;
  let removeFxModeListener: () => void = () => {};

  const selectedNode = reactive<SelectedNodeState>({
    groupKey: "",
    subgroupId: "",
    itemId: "",
  });

  const expandedGroups = reactive<Record<string, boolean>>({});
  const healthStates = reactive<Record<string, DashboardHealthState>>({});
  const dragState = reactive<DragState>({
    type: "",
    groupId: "",
    subgroupId: "",
    itemId: "",
  });
  const itemFaviconFailures = reactive<Record<string, boolean>>({});
  const persistedUiState = loadPersistedUiState(UI_STATE_STORAGE_KEY);

  if (persistedUiState) {
    const persistedCardView = String(persistedUiState.serviceCardView || "");
    if (SERVICE_CARD_VIEW_VALUES.has(persistedCardView)) {
      serviceCardView.value = persistedCardView as ServiceCardView;
    }

    const persistedGrouping = String(
      persistedUiState.serviceGroupingMode || "",
    );
    if (SERVICE_GROUPING_VALUES.has(persistedGrouping)) {
      serviceGroupingMode.value = persistedGrouping as ServiceGroupingMode;
    }

    const persistedSidebarView = String(persistedUiState.sidebarView || "");
    if (
      SIDEBAR_VIEW_SEQUENCE.includes(persistedSidebarView as SidebarViewMode)
    ) {
      sidebarView.value = persistedSidebarView as SidebarViewMode;
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
      selectedNode.groupKey = String(
        (persistedSelectedNode as Partial<SelectedNodeState>).groupKey || "",
      );
      selectedNode.subgroupId = String(
        (persistedSelectedNode as Partial<SelectedNodeState>).subgroupId || "",
      );
      selectedNode.itemId = String(
        (persistedSelectedNode as Partial<SelectedNodeState>).itemId || "",
      );
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

  const iframeModal = reactive<IframeModalState>({
    open: false,
    title: "",
    src: "",
    allow: "",
    sandbox: false,
    sandboxAttribute: "",
    referrerPolicy: "",
    loading: false,
    error: "",
  });

  const itemEditor = reactive<ItemEditorState>({
    open: false,
    mode: "create",
    groupId: "",
    subgroupId: "",
    originalItemId: "",
    submitting: false,
    error: "",
    form: defaultItemEditorForm(),
  });
  const createChooser = reactive<CreateChooserState>({
    open: false,
    groupId: "",
    subgroupId: "",
  });
  const createEntityEditor = reactive<CreateEntityState>({
    open: false,
    submitting: false,
    error: "",
    form: defaultCreateEntityForm(),
  });

  const pages = computed<DashboardLayoutPage[]>(() => {
    if (!config.value) return [];
    return config.value?.layout?.pages || [];
  });

  function normalizeWidget(widget: DashboardWidget): DashboardWidgetResolved {
    const rawData = widget.data || {};
    const columns: DashboardWidgetColumn[] = Array.isArray(rawData.columns)
      ? rawData.columns
          .map((column) => {
            const normalizedColumn =
              column && typeof column === "object"
                ? (column as Record<string, unknown>)
                : null;
            const key = String(normalizedColumn?.key || "").trim();
            if (!key) return null;
            return {
              ...normalizedColumn,
              key,
              title: String(normalizedColumn?.title || key),
            } as DashboardWidgetColumn;
          })
          .filter((column): column is DashboardWidgetColumn => Boolean(column))
      : [];
    const actions: DashboardWidgetAction[] = Array.isArray(rawData.actions)
      ? rawData.actions
          .map((action) => {
            const normalizedAction =
              action && typeof action === "object"
                ? (action as Record<string, unknown>)
                : null;
            const id = String(normalizedAction?.id || "").trim();
            if (!id) return null;
            return {
              ...normalizedAction,
              id,
              title: String(normalizedAction?.title || id),
            } as DashboardWidgetAction;
          })
          .filter((action): action is DashboardWidgetAction => Boolean(action))
      : [];

    return {
      ...widget,
      title: String(widget.title || widget.id),
      data: {
        ...rawData,
        columns,
        actions,
      },
      actions,
    };
  }

  const widgets = computed<DashboardWidgetResolved[]>(() =>
    (config.value?.widgets || []).map((widget) => normalizeWidget(widget)),
  );
  const authProfileOptions = computed<AuthProfile[]>(
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
  const saveStatusLabel = computed(() => {
    if (saveStatus.value === "saving") return "Сохранение...";
    if (saveStatus.value === "saved") return "Сохранено";
    if (saveStatus.value === "error") return "Ошибка сохранения";
    return editMode.value ? "Готово" : "Сохранение выключено";
  });
  const siteFilterOptions = computed<Array<{ value: string; label: string }>>(
    () => {
      const sitesMap = new Map<string, string>();
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
    },
  );

  const widgetById = computed(() => {
    const map = new Map<string, DashboardWidgetResolved>();
    for (const widget of widgets.value) {
      map.set(widget.id, widget);
    }
    return map;
  });

  const groupById = computed(() => {
    const map = new Map<string, DashboardGroup>();
    for (const group of config.value?.groups || []) {
      map.set(group.id, group);
    }
    return map;
  });

  const subgroupById = computed(() => {
    const map = new Map<
      string,
      { group: DashboardGroup; subgroup: DashboardSubgroup }
    >();
    for (const group of config.value?.groups || []) {
      for (const subgroup of group.subgroups || []) {
        map.set(subgroup.id, { group, subgroup });
      }
    }
    return map;
  });
  const createEntityGroupOptions = computed(() =>
    (config.value?.groups || []).map((group) => ({
      id: String(group.id || ""),
      title: String(group.title || group.id || ""),
    })),
  );
  const createEntityDashboardOptions = computed(() =>
    pages.value.map((page) => ({
      id: String(page.id || ""),
      title: String(page.title || page.id || ""),
    })),
  );
  const createEntityItemGroupOptions = computed(() => {
    const dashboardId = String(createEntityEditor.form.parentDashboardId || "");
    const groupIds = resolveGroupIdsForDashboard(dashboardId);
    return groupIds
      .map((groupId) => {
        const group = groupById.value.get(groupId);
        if (!group) return null;
        return {
          id: String(group.id || ""),
          title: String(group.title || group.id || ""),
        };
      })
      .filter((entry): entry is { id: string; title: string } =>
        Boolean(entry),
      );
  });
  const createEntitySubgroupOptions = computed(() => {
    const groupId = String(createEntityEditor.form.parentGroupId || "");
    const group = groupById.value.get(groupId);
    if (!group) return [];
    return (group.subgroups || []).map((subgroup) => ({
      id: String(subgroup.id || ""),
      title: String(subgroup.title || subgroup.id || ""),
    }));
  });

  const pageByBlockGroupId = computed(() => {
    const map = new Map<string, string>();
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
    return new Map<string, string>();
  });

  const commandPaletteEntries = computed<CommandPaletteEntry[]>(() => {
    const entries: CommandPaletteEntry[] = [];
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
    entries.push({
      id: "action:open-plugin-panel",
      type: "action",
      action: "open_plugin_panel",
      item: null,
      title: "Открыть панель плагинов",
      titleLower: "открыть панель плагинов",
      host: "",
      ip: "",
      site: "",
      tagsLower: [],
      groupId: "",
      groupKey: "",
      groupTitle: "Команда",
      subgroupId: "",
      subgroupTitle: "Плагины",
      pageId: "",
      searchBlob:
        "открыть панель плагинов plugins plugin store расширения extensions",
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

  const commandPaletteResults = computed<CommandPaletteEntry[]>(() => {
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
    const scored: Array<{ entry: CommandPaletteEntry; score: number }> = [];
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

  const activePageGroupRefs = computed<string[]>(() => {
    if (!activePage.value) return [];
    const refs = new Set<string>();
    for (const block of activePage.value.blocks || []) {
      if (block?.type !== "groups") continue;
      for (const groupId of block.group_ids || []) {
        const normalizedId = String(groupId || "").trim();
        if (normalizedId) refs.add(normalizedId);
      }
    }
    return Array.from(refs);
  });

  const treeGroups = computed<TreeGroupNode[]>(() => {
    return resolveBlockGroups(activePageGroupRefs.value);
  });

  const filteredTreeGroups = computed<TreeGroupNode[]>(() => {
    const bySite = filterGroupsBySite(treeGroups.value);
    const queryTokens = treeFilter.value
      .trim()
      .toLowerCase()
      .split(/\s+/)
      .filter(Boolean);
    if (!queryTokens.length) return bySite;

    const matchesQueryTokens = (...parts: Array<unknown>): boolean => {
      const searchableText = parts
        .flatMap((part) =>
          Array.isArray(part)
            ? part.map((entry) => String(entry || ""))
            : [String(part || "")],
        )
        .map((chunk) => chunk.trim().toLowerCase())
        .filter(Boolean)
        .join(" ");
      if (!searchableText) return false;
      return queryTokens.every((token) => searchableText.includes(token));
    };

    return bySite
      .map((group) => {
        const groupMatches = matchesQueryTokens(
          group.title,
          group.name,
          group.description,
          group.id,
        );

        if (groupMatches) {
          return {
            ...group,
            subgroups: group.subgroups || [],
          };
        }

        const matchedSubgroups = (group.subgroups || [])
          .map((subgroup) => {
            const subgroupMatches = matchesQueryTokens(
              subgroup.title,
              subgroup.name,
              subgroup.description,
              subgroup.id,
            );
            if (subgroupMatches) {
              return {
                ...subgroup,
                items: subgroup.items || [],
              };
            }

            const matchedItems = (subgroup.items || []).filter((item) => {
              const rawItem = item as Record<string, unknown>;
              return matchesQueryTokens(
                item.id,
                item.title,
                rawItem.name,
                rawItem.description,
                rawItem.desc,
                item.url,
                rawItem.check_url,
                item.tags || [],
                resolveItemSite(item, group),
              );
            });

            if (!matchedItems.length) return null;
            return {
              ...subgroup,
              items: matchedItems,
            };
          })
          .filter((subgroup): subgroup is DashboardSubgroup =>
            Boolean(subgroup),
          );

        if (!matchedSubgroups.length) return null;
        return {
          ...group,
          subgroups: matchedSubgroups,
        };
      })
      .filter((group): group is TreeGroupNode => Boolean(group));
  });

  const sidebarIconNodes = computed<SidebarIconNode[]>(() => {
    const nodes: SidebarIconNode[] = [];

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

  const visibleTreeItemIds = computed<string[]>(() => {
    const ids: string[] = [];
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

  const activePageWidgetIds = computed<string[]>(() => {
    if (!activePage.value) return [];

    const ids: string[] = [];
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

  const activePageGroupBlocks = computed<DashboardLayoutBlock[]>(() =>
    (activePage.value?.blocks || []).filter(
      (block) => block?.type === "groups",
    ),
  );

  const activeIndicatorWidget = computed<DashboardWidgetResolved | null>(() => {
    const widget = widgetById.value.get(activeIndicatorViewId.value);
    if (!widget || !isLargeIndicator(widget)) return null;
    return activePageWidgetIds.value.includes(widget.id) ? widget : null;
  });

  const sectionCtx: any = {
    EVENTS_STREAM_PATH,
    EVENT_STREAM_RECONNECT_MS,
    LARGE_INDICATOR_TYPES,
    SIDEBAR_PARTICLES_CONFIG,
    SIDEBAR_PARTICLES_ID,
    SIDEBAR_VIEW_SEQUENCE,
    activeIndicatorViewId,
    activePageId,
    actionBusy,
    authProfileOptions,
    commandPaletteActiveIndex,
    commandPaletteOpen,
    commandPaletteQuery,
    commandPaletteResults,
    config,
    configError,
    createChooser,
    createEntityEditor,
    createEntityGroupOptions,
    defaultCreateEntityForm,
    defaultItemEditorForm,
    dragState,
    editMode,
    ensureAbsoluteHttpUrl,
    ensurePageGroupsReferenceInConfig,
    ensureParticlesJs,
    errorMessage,
    expandedGroups,
    fetchDashboardConfig,
    groupById,
    healthStates,
    iframeModal,
    isDocumentVisible,
    isSidebarDetailed,
    isSidebarHidden,
    itemEditor,
    itemFaviconFailures,
    itemIpById,
    loadingConfig,
    moveGroupInConfig,
    moveItemBeforeInConfig,
    moveItemToSubgroupEndInConfig,
    moveSubgroupInConfig,
    normalizeId,
    normalizeLayoutBlocksInConfig,
    pages,
    pageByBlockGroupId,
    requestJson,
    resolveGroupIconSemantic,
    resolveItemIconSemantic,
    resolvePageIconSemantic,
    resolveRequestUrl,
    resolveSubgroupIconSemantic,
    resolveWidgetIconSemantic,
    saveError,
    saveStatus,
    selectedNode,
    serviceCardView,
    serviceGroupingMode,
    settingsPanel,
    sidebarIndicators,
    siteFilter,
    siteFilterOptions,
    subgroupById,
    treeFilter,
    treeGroups,
    updateDashboardConfig,
    visibleTreeItemIds,
    widgetById,
    widgetIntervals,
    widgetStates,
    widgets,
    connectOkoSseStream,
    goSettings,
    goPluginsPanel,
  };

  Object.defineProperties(sectionCtx, {
    healthStream: {
      get: () => healthStream,
      set: (value: OkoSseStream | null) => {
        healthStream = value;
      },
    },
    healthStreamReconnectTimer: {
      get: () => healthStreamReconnectTimer,
      set: (value: number) => {
        healthStreamReconnectTimer = value;
      },
    },
    saveStatusTimer: {
      get: () => saveStatusTimer,
      set: (value: number) => {
        saveStatusTimer = value;
      },
    },
    visibilitySyncInFlight: {
      get: () => visibilitySyncInFlight,
      set: (value: boolean) => {
        visibilitySyncInFlight = value;
      },
    },
    particlesReinitRaf: {
      get: () => particlesReinitRaf,
      set: (value: number) => {
        particlesReinitRaf = value;
      },
    },
    preserveTreeSelectionOnPageSwitch: {
      get: () => preserveTreeSelectionOnPageSwitch,
      set: (value: boolean) => {
        preserveTreeSelectionOnPageSwitch = value;
      },
    },
    originFromHttpUrl: {
      value: originFromHttpUrl,
      writable: false,
    },
  });

  Object.assign(sectionCtx, createDashboardCreateEntitySection(sectionCtx));
  Object.assign(sectionCtx, createDashboardConfigMutationSection(sectionCtx));

  const crudSection = createDashboardCrudSection(sectionCtx);
  Object.assign(sectionCtx, crudSection);

  Object.assign(sectionCtx, createDashboardUiStyleSection(sectionCtx));
  Object.assign(sectionCtx, createDashboardIndicatorsSection(sectionCtx));
  Object.assign(sectionCtx, createDashboardTreeDataSection(sectionCtx));
  Object.assign(sectionCtx, createDashboardTreeSelectionSection(sectionCtx));
  Object.assign(sectionCtx, createDashboardGroupingSection(sectionCtx));
  Object.assign(sectionCtx, createDashboardWidgetRuntimeSection(sectionCtx));
  Object.assign(sectionCtx, createDashboardHealthSection(sectionCtx));
  Object.assign(sectionCtx, createDashboardConfigLoadSection(sectionCtx));
  Object.assign(sectionCtx, createDashboardItemActionsSection(sectionCtx));
  Object.assign(sectionCtx, createDashboardFxSection(sectionCtx));
  Object.assign(sectionCtx, createDashboardIconsSection(sectionCtx));
  Object.assign(sectionCtx, createDashboardCommandPaletteSection(sectionCtx));

  const resolveGroupIdsForDashboard = (dashboardId: string): string[] =>
    sectionCtx.resolveGroupIdsForDashboard(dashboardId);
  const resolveItemSite = (
    item: DashboardItem | null | undefined,
    group: Record<string, unknown> | null = null,
  ): string => sectionCtx.resolveItemSite(item, group);
  const safeUrlHost = (rawValue: unknown): string =>
    sectionCtx.safeUrlHost(rawValue);
  const resolveBlockGroups = (
    groupIds: readonly string[] = [],
  ): TreeGroupNode[] => sectionCtx.resolveBlockGroups(groupIds);
  const filterGroupsBySite = (groups: TreeGroupNode[] = []): TreeGroupNode[] =>
    sectionCtx.filterGroupsBySite(groups);
  const healthState = (itemId: string): DashboardHealthState | null =>
    sectionCtx.healthState(itemId);
  const isWidgetBlock = (block: DashboardLayoutBlock): boolean =>
    sectionCtx.isWidgetBlock(block);
  const resolveWidgets = (
    widgetIds: readonly string[] = [],
  ): DashboardWidgetResolved[] => sectionCtx.resolveWidgets(widgetIds);
  const isLargeIndicator = (widget: DashboardWidget): boolean =>
    sectionCtx.isLargeIndicator(widget);

  let hasInitializedActivePage = false;

  watch(
    () => activePage.value?.id,
    () => {
      if (hasInitializedActivePage) {
        activeIndicatorViewId.value = "";
        if (!preserveTreeSelectionOnPageSwitch) {
          treeFilter.value = "";
          sectionCtx.clearSelectedNode();
        }
        preserveTreeSelectionOnPageSwitch = false;
      } else {
        hasInitializedActivePage = true;
      }
      sectionCtx.syncTreeGroupsState();
      sectionCtx.refreshHealth();
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
      sectionCtx.syncTreeGroupsState();
      sectionCtx.refreshHealth();
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
    () => visibleTreeItemIds.value.length,
    (count) => {
      sectionCtx.applyMotionBudgetProfile(count);
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
      savePersistedUiState(UI_STATE_STORAGE_KEY, snapshot);
    },
    { deep: true },
  );

  onMounted(async () => {
    window.addEventListener(
      "visibilitychange",
      sectionCtx.handleDocumentVisibilityChange,
    );
    removeFxModeListener = onOkoEvent(
      EVENT_FX_MODE_CHANGE,
      sectionCtx.handleFxModeChange,
    );
    await sectionCtx.initSidebarParticles();
    await sectionCtx.loadConfig();
  });

  onBeforeUnmount(() => {
    sectionCtx.resetWidgetPolling();
    sectionCtx.stopHealthPolling();
    window.removeEventListener(
      "visibilitychange",
      sectionCtx.handleDocumentVisibilityChange,
    );
    removeFxModeListener();
    removeFxModeListener = () => {};
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

    options.onDispose?.();
  });

  return {
    ...sectionCtx,
    BRAND_ICON_BY_KEY,
    DEFAULT_ITEM_URL,
    EMBLEM_SRC,
    ICON_BY_KEY,
    ICON_RULES,
    LARGE_INDICATOR_TYPES,
    SIDEBAR_PARTICLES_CONFIG,
    SIDEBAR_PARTICLES_ID,
    activeIndicatorViewId,
    activePageId,
    authProfileOptions,
    commandPaletteActiveIndex,
    commandPaletteOpen,
    commandPaletteQuery,
    config,
    configError,
    createChooser,
    createEntityEditor,
    createEntityGroupOptions,
    dragState,
    editMode,
    expandedGroups,
    groupById,
    healthStates,
    iframeModal,
    itemEditor,
    itemFaviconFailures,
    loadingConfig,
    saveError,
    saveStatus,
    selectedNode,
    serviceCardView,
    serviceGroupingMode,
    settingsPanel,
    siteFilter,
    siteFilterOptions,
    sidebarView,
    subgroupById,
    treeFilter,
    treeGroups,
    widgetById,
    widgetIntervals,
    widgetStates,
    widgets,
    activeCommandPaletteEntry,
    activeIndicatorWidget,
    activePage,
    activePageGroupBlocks,
    activePageWidgetIds,
    allItemIds,
    allSubgroupIds,
    appTagline,
    appTitle,
    createBrandIcon,
    createEntityDashboardOptions,
    createEntityItemGroupOptions,
    createEntitySubgroupOptions,
    ensurePageGroupsReference,
    filteredTreeGroups,
    findGroup,
    findSubgroup,
    fromToken,
    isCompactServiceCardView,
    isIconCardView,
    isSidebarIconOnly,
    isTileCardView,
    makeUniqueId,
    moveGroup,
    moveItemBefore,
    moveItemToSubgroupEnd,
    moveSubgroup,
    normalizeIconToken,
    normalizeLayoutBlocks,
    pageHealthSummary,
    pickSemanticIcon,
    saveStatusLabel,
    serviceGroupingOptions,
    servicePresentationOptions,
    sidebarIconNodes,
    sidebarIndicatorSummary,
    sidebarViewToggleTitle,
    statsExpanded,
  };
}
