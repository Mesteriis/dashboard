<template>
  <UiBlankLayout
    class="plugins-panel-layout"
    :emblem-src="EMBLEM_SRC"
    :sidebar-hidden="isSidebarHidden"
    :sidebar-particles-id="SIDEBAR_PARTICLES_ID"
    content-label="Plugin center content"
  >
    <template #sidebar-mid>
      <section class="sidebar-tree" aria-label="Node tree плагинов">
        <ul v-if="sidebarTreeGroups.length" class="tree-root">
          <li
            v-for="group in sidebarTreeGroups"
            :key="group.id"
            class="tree-group-item"
          >
            <div class="tree-node-row">
              <UiSidebarListItem variant="group" :active="true">
                <span class="tree-caret open">▾</span>
                <LayoutGrid class="ui-icon tree-icon" />
                <span class="tree-text">{{ group.label }}</span>
                <span class="tree-meta">{{ group.items.length }}</span>
              </UiSidebarListItem>
            </div>

            <ul class="tree-items">
              <li
                v-for="item in group.items"
                :key="item.id"
                class="tree-item-row"
              >
                <div class="tree-node-row">
                  <UiSidebarListItem
                    variant="item"
                    :active="activeTreeNodeId === item.id"
                    :disabled="item.disabled"
                    @click="handleTreeNodeClick(item)"
                  >
                    <Package class="ui-icon tree-icon tree-item-icon" />
                    <span class="tree-text">{{ item.label }}</span>
                  </UiSidebarListItem>
                </div>
              </li>
            </ul>
          </li>
        </ul>

        <p v-else class="tree-empty">Для выбранного раздела нет элементов.</p>
      </section>
    </template>

    <template #sidebar-bottom-indicators>
      <section class="plugins-install-actions" aria-label="Установка плагинов">
        <input
          ref="zipInputRef"
          class="plugins-install-zip-input"
          type="file"
          accept=".zip,application/zip"
          @change="handleZipInputChange"
        />

        <button
          class="plugins-install-btn"
          type="button"
          :disabled="installActionsDisabled"
          @click="handleInstallZipClick"
        >
          <FileArchive class="ui-icon" />
          <span>Установить ZIP</span>
        </button>

        <button
          class="plugins-install-btn"
          type="button"
          :disabled="installActionsDisabled"
          @click="handleInstallGithubLinkClick"
        >
          <Github class="ui-icon" />
          <span>Установить GitHub link</span>
        </button>
      </section>
    </template>

    <template #header-tabs>
      <nav
        class="hero-page-tabs plugins-main-tabs"
        role="tablist"
        aria-label="Вкладки панели плагинов"
      >
        <button
          class="hero-page-tab-btn"
          :class="{ active: activeTab === 'installed' }"
          type="button"
          role="tab"
          :aria-selected="activeTab === 'installed'"
          @click="setActiveTab('installed')"
        >
          <Package class="ui-icon hero-page-tab-icon" />
          <span v-if="activeTab === 'installed'" class="hero-page-tab-label"
            >Установленные плагины</span
          >
          <strong v-if="activeTab === 'installed'">{{
            installedPlugins.length
          }}</strong>
        </button>

        <button
          class="hero-page-tab-btn"
          :class="{ active: activeTab === 'store' }"
          type="button"
          role="tab"
          :aria-selected="activeTab === 'store'"
          @click="setActiveTab('store')"
        >
          <Store class="ui-icon hero-page-tab-icon" />
          <span v-if="activeTab === 'store'" class="hero-page-tab-label"
            >Store</span
          >
          <strong v-if="activeTab === 'store'">{{ storeCounterLabel }}</strong>
        </button>

        <button
          class="hero-page-tab-btn"
          :class="{ active: activeTab === 'settings' }"
          type="button"
          role="tab"
          :aria-selected="activeTab === 'settings'"
          @click="setActiveTab('settings')"
        >
          <Settings class="ui-icon hero-page-tab-icon" />
          <span v-if="activeTab === 'settings'" class="hero-page-tab-label"
            >Settings</span
          >
          <strong v-if="activeTab === 'settings'">beta</strong>
        </button>
      </nav>
    </template>

    <template #canvas-main>
      <section
        v-if="activeTab === 'installed'"
        class="plugins-panel-content plugins-main-surface"
        role="tabpanel"
        aria-label="Установленные плагины"
      >
        <header class="plugins-main-surface-head">
          <h3>Все плагины</h3>
          <p>Расширения, подключенные в текущей конфигурации.</p>
        </header>

        <section class="plugins-main-tile-wrap" aria-label="Плитка плагинов">
          <header class="plugins-main-tile-head">
            <h4>Плитка</h4>
          </header>

          <div v-if="installedPlugins.length" class="plugins-main-tile-grid">
            <article
              v-for="plugin in installedPlugins"
              :key="plugin.id"
              class="plugins-main-tile-card"
            >
              <header>
                <h5>{{ plugin.title }}</h5>
                <span class="plugins-main-tile-chip">plugin</span>
              </header>
              <p class="plugins-main-tile-id">{{ plugin.id }}</p>
              <p class="plugins-main-tile-meta">
                {{ plugin.serviceCount }} сервисов ·
                {{ plugin.elementsCount }} UI
              </p>
              <div class="plugins-main-tile-actions">
                <button
                  class="ghost"
                  type="button"
                  @click="openPlugin(plugin.id)"
                >
                  Открыть
                </button>
                <button class="ghost" type="button">Проверить</button>
              </div>
            </article>
          </div>

          <div v-else class="plugins-empty-state">
            <h3>Пока нет установленных плагинов</h3>
            <p>После подключения расширений они появятся в этом списке.</p>
          </div>
        </section>
      </section>

      <section
        v-else-if="activeTab === 'store'"
        class="plugins-panel-content plugins-main-surface"
        role="tabpanel"
        aria-label="Store"
      >
        <header class="plugins-main-surface-head">
          <h3>Store</h3>
          <p>Доступные плагины для установки.</p>
        </header>
        <section class="plugins-main-tile-wrap">
          <div v-if="loadingStore" class="plugins-empty-state">
            <h3>Загрузка Store</h3>
            <p>Получаем список плагинов...</p>
          </div>

          <div v-else-if="storePlugins.length" class="plugins-main-tile-grid">
            <article
              v-for="plugin in storePlugins"
              :key="plugin.id"
              class="plugins-main-tile-card"
            >
              <header>
                <h5>{{ plugin.title }}</h5>
                <span class="plugins-main-tile-chip">{{
                  plugin.installed ? "installed" : "store"
                }}</span>
              </header>
              <p class="plugins-main-tile-id">{{ plugin.id }}</p>
              <p class="plugins-main-tile-meta">
                {{ plugin.version ? `v${plugin.version}` : "version n/a" }} ·
                {{ plugin.source || "source n/a" }}
              </p>
              <p v-if="plugin.description" class="plugins-main-tile-meta">
                {{ plugin.description }}
              </p>
              <div class="plugins-main-tile-actions">
                <button
                  v-if="plugin.installed && plugin.openPluginId"
                  class="ghost"
                  type="button"
                  @click="openPlugin(plugin.openPluginId)"
                >
                  Открыть
                </button>
                <button
                  v-else
                  class="ghost"
                  type="button"
                  :disabled="isInstallingStorePlugin(plugin.id)"
                  @click="installStorePlugin(plugin)"
                >
                  {{
                    isInstallingStorePlugin(plugin.id)
                      ? "Установка..."
                      : "Установить"
                  }}
                </button>
              </div>
            </article>
          </div>

          <p
            v-if="storeActionMessage"
            class="plugins-main-tile-meta"
            :class="{ 'plugins-store-error': storeActionStatus === 'error' }"
          >
            {{ storeActionMessage }}
          </p>

          <div v-else-if="storeAvailable === false" class="plugins-empty-state">
            <h3>Store недоступен</h3>
            <p>Backend вернул статус unavailable для каталога плагинов.</p>
          </div>

          <div v-else class="plugins-empty-state">
            <h3>В Store пока нет плагинов</h3>
            <p>Когда плагины появятся в каталоге, они отобразятся здесь.</p>
          </div>
        </section>
      </section>

      <section
        v-else
        class="plugins-panel-content plugins-main-surface"
        role="tabpanel"
        aria-label="Plugin settings"
      >
        <header class="plugins-main-surface-head">
          <h3>Plugin settings</h3>
          <p>Global defaults for plugin runtime and security.</p>
        </header>
        <section class="plugins-main-tile-wrap">
          <div class="plugins-empty-state">
            <h3>Settings section is in progress</h3>
            <p>URL-synced tab state is active and ready for extension.</p>
          </div>
        </section>
      </section>
    </template>
  </UiBlankLayout>

  <UiBaseModal
    :open="githubInstallModal.open"
    backdrop-class="plugins-github-modal-backdrop"
    modal-class="plugins-github-modal"
    @backdrop="closeGithubInstallModal"
  >
    <header class="plugins-github-modal-head">
      <div>
        <h3>Установка из GitHub</h3>
        <p>Вставьте ссылку на репозиторий плагина.</p>
      </div>
      <button
        class="ghost plugins-github-modal-close"
        type="button"
        aria-label="Закрыть окно установки из GitHub"
        @click="closeGithubInstallModal"
      >
        <X class="ui-icon" />
      </button>
    </header>

    <label class="plugins-github-field">
      <Github class="ui-icon plugins-github-field-icon" />
      <input
        ref="githubInputRef"
        v-model.trim="githubInstallModal.link"
        type="text"
        autocomplete="off"
        spellcheck="false"
        placeholder="https://github.com/owner/repo"
        @keydown.enter.prevent="checkGithubLink"
      />
    </label>

    <p
      v-if="githubInstallModal.message"
      class="plugins-github-status"
      :class="{
        ok: githubInstallModal.status === 'ok',
        error: githubInstallModal.status === 'error',
      }"
      role="status"
      aria-live="polite"
    >
      {{ githubInstallModal.message }}
    </p>

    <div class="plugins-github-actions">
      <button class="ghost" type="button" @click="closeGithubInstallModal">
        Отмена
      </button>
      <button class="plugins-github-check-btn" type="button" @click="checkGithubLink">
        Проверить
      </button>
      <button
        class="plugins-github-install-btn"
        type="button"
        @click="submitGithubInstall"
      >
        Установить
      </button>
    </div>
  </UiBaseModal>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from "vue";
import {
  FileArchive,
  Github,
  LayoutGrid,
  Package,
  Settings,
  Store,
  X,
} from "lucide-vue-next";
import UiBaseModal from "@/ui/overlays/UiBaseModal.vue";
import UiBlankLayout from "@/components/layout/UiBlankLayout.vue";
import UiSidebarListItem from "@/components/navigation/UiSidebarListItem.vue";
import { requestJson } from "@/features/services/dashboardApi";
import {
  EMBLEM_SRC,
  SIDEBAR_PARTICLES_CONFIG,
  SIDEBAR_PARTICLES_ID,
} from "@/features/stores/ui/storeConstants";
import { useUiStore } from "@/features/stores/uiStore";
import { useSidebarParticles } from "@/features/composables/useSidebarParticles";

type PluginPanelTab = "installed" | "store" | "settings";

interface InstalledPlugin {
  id: string;
  title: string;
  serviceCount: number;
  elementsCount: number;
}

interface StorePlugin {
  id: string;
  title: string;
  version: string;
  description: string;
  source: string;
  installed: boolean;
  openPluginId: string;
}

interface PluginUsageEntry {
  id: string;
  title: string;
  serviceIds: Set<string>;
  elementsCount: number;
  groupLabels: Set<string>;
}

interface TreeNodeItem {
  id: string;
  label: string;
  pluginId: string;
  disabled: boolean;
}

interface TreeNodeGroup {
  id: string;
  label: string;
  items: TreeNodeItem[];
}

const props = withDefaults(
  defineProps<{
    tab: PluginPanelTab;
  }>(),
  {
    tab: "store",
  },
);

const emit = defineEmits<{
  setTab: [tab: PluginPanelTab];
  openPlugin: [pluginId: string];
}>();

const dashboard = useUiStore();
const { config, isSidebarHidden } = dashboard;

useSidebarParticles({
  containerId: SIDEBAR_PARTICLES_ID,
  baseConfig: SIDEBAR_PARTICLES_CONFIG,
  isSidebarHidden,
});
const zipInputRef = ref<HTMLInputElement | null>(null);
const githubInputRef = ref<HTMLInputElement | null>(null);
const githubInstallModal = reactive<{
  open: boolean;
  link: string;
  message: string;
  status: "idle" | "ok" | "error";
}>({
  open: false,
  link: "",
  message: "",
  status: "idle",
});

const activeTab = computed<PluginPanelTab>(() => props.tab);
const activeTreeNodeId = ref("");
const installActionsDisabled = true;

const installedPluginsApi = ref<unknown[]>([]);
const storePluginsApi = ref<unknown[]>([]);
const storeAvailable = ref<boolean | null>(null);
const storeTotal = ref<number | null>(null);
const loadingStore = ref(false);
const installingStorePlugins = reactive<Record<string, boolean>>({});
const storeActionStatus = ref<"idle" | "success" | "error">("idle");
const storeActionMessage = ref("");

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

function asNonEmptyString(value: unknown): string {
  return String(value || "").trim();
}

function extractPluginsList(payload: unknown): unknown[] {
  if (Array.isArray(payload)) return payload;
  const record = asRecord(payload);
  if (!record) return [];
  if (Array.isArray(record.plugins)) return record.plugins;
  const nestedData = asRecord(record.data);
  if (nestedData && Array.isArray(nestedData.plugins)) return nestedData.plugins;
  return [];
}

function extractStoreAvailable(payload: unknown): boolean | null {
  const record = asRecord(payload);
  if (!record) return null;
  if (typeof record.available === "boolean") return record.available;
  const nestedData = asRecord(record.data);
  if (nestedData && typeof nestedData.available === "boolean") {
    return nestedData.available;
  }
  return null;
}

function extractStoreTotal(payload: unknown): number | null {
  const record = asRecord(payload);
  if (!record) return null;
  const directTotal = Number(record.total);
  if (Number.isFinite(directTotal) && directTotal >= 0) return directTotal;
  const nestedData = asRecord(record.data);
  const nestedTotal = Number(nestedData?.total);
  if (Number.isFinite(nestedTotal) && nestedTotal >= 0) return nestedTotal;
  return null;
}

function messageFromError(error: unknown): string {
  if (error instanceof Error) {
    return String(error.message || "Unknown error");
  }
  return "Unknown error";
}

async function loadInstalledPlugins(): Promise<void> {
  try {
    const response = await requestJson("/api/v1/plugins");
    installedPluginsApi.value = extractPluginsList(response);
  } catch {
    installedPluginsApi.value = [];
  }
}

async function loadStorePlugins(): Promise<void> {
  loadingStore.value = true;
  try {
    const response = await requestJson("/api/v1/store");
    storeAvailable.value = extractStoreAvailable(response);
    storeTotal.value = extractStoreTotal(response);
    storePluginsApi.value = extractPluginsList(response);
  } catch {
    storeAvailable.value = false;
    storeTotal.value = null;
    storePluginsApi.value = [];
  } finally {
    loadingStore.value = false;
  }
}

const pluginUsageRegistry = computed<Map<string, PluginUsageEntry>>(() => {
  const usageRegistry = new Map<string, PluginUsageEntry>();

  for (const group of config.value?.groups || []) {
    const groupLabel = String(group.title || group.id || "").trim();
    for (const subgroup of group.subgroups || []) {
      for (const item of subgroup.items || []) {
        const rawItem = item as Record<string, unknown>;
        const pluginBlocks = Array.isArray(rawItem.plugin_blocks)
          ? rawItem.plugin_blocks
          : [];

        for (const block of pluginBlocks) {
          if (!block || typeof block !== "object" || Array.isArray(block))
            continue;
          const rawBlock = block as Record<string, unknown>;
          const pluginId = String(rawBlock.plugin_id || "").trim();
          if (!pluginId) continue;

          const existing = usageRegistry.get(pluginId) || {
            id: pluginId,
            title: pluginId,
            serviceIds: new Set<string>(),
            elementsCount: 0,
            groupLabels: new Set<string>(),
          };

          const pluginTitle = String(rawBlock.title || "").trim();
          if (pluginTitle) {
            existing.title = pluginTitle;
          }

          const serviceId = String(rawItem.id || "").trim();
          if (serviceId) {
            existing.serviceIds.add(serviceId);
          }

          const elements = Array.isArray(rawBlock.elements)
            ? rawBlock.elements
            : [];
          existing.elementsCount += elements.length;
          if (groupLabel) {
            existing.groupLabels.add(groupLabel);
          }

          usageRegistry.set(pluginId, existing);
        }
      }
    }
  }

  return usageRegistry;
});

const installedPlugins = computed<InstalledPlugin[]>(() => {
  const usageRegistry = pluginUsageRegistry.value;

  const result = new Map<string, InstalledPlugin>();

  for (const rawEntry of installedPluginsApi.value) {
    const entry = asRecord(rawEntry);
    if (!entry) continue;
    const id = asNonEmptyString(entry.id) || asNonEmptyString(entry.name);
    if (!id) continue;

    const manifest = asRecord(entry.manifest);
    const title =
      asNonEmptyString(entry.title) ||
      asNonEmptyString(entry.name) ||
      asNonEmptyString(manifest?.title) ||
      asNonEmptyString(manifest?.name) ||
      id;

    const usage = usageRegistry.get(id);
    result.set(id, {
      id,
      title,
      serviceCount: usage?.serviceIds.size || 0,
      elementsCount: usage?.elementsCount || 0,
    });
  }

  for (const usage of usageRegistry.values()) {
    if (result.has(usage.id)) continue;
    result.set(usage.id, {
      id: usage.id,
      title: usage.title,
      serviceCount: usage.serviceIds.size,
      elementsCount: usage.elementsCount,
    });
  }

  return Array.from(result.values())
    .sort((left, right) =>
      left.title.localeCompare(right.title, "ru", { sensitivity: "base" }),
    );
});

const installedPluginIds = computed<Set<string>>(
  () => new Set(installedPlugins.value.map((plugin) => plugin.id)),
);

const storePlugins = computed<StorePlugin[]>(() => {
  const result: StorePlugin[] = [];
  const installedIds = installedPluginIds.value;

  for (const rawEntry of storePluginsApi.value) {
    const entry = asRecord(rawEntry);
    if (!entry) continue;
    const manifest = asRecord(entry.manifest);

    const id =
      asNonEmptyString(entry.id) ||
      asNonEmptyString(entry.name) ||
      asNonEmptyString(manifest?.name);
    if (!id) continue;

    const runtimeId =
      asNonEmptyString(entry.name) ||
      asNonEmptyString(manifest?.name) ||
      id;
    const openPluginId = installedIds.has(runtimeId)
      ? runtimeId
      : installedIds.has(id)
        ? id
        : "";

    result.push({
      id,
      title:
        asNonEmptyString(entry.title) ||
        asNonEmptyString(entry.name) ||
        asNonEmptyString(manifest?.title) ||
        asNonEmptyString(manifest?.name) ||
        runtimeId,
      version:
        asNonEmptyString(entry.version) ||
        asNonEmptyString(manifest?.version),
      description:
        asNonEmptyString(entry.description) ||
        asNonEmptyString(manifest?.description),
      source: asNonEmptyString(entry.source),
      installed: Boolean(openPluginId),
      openPluginId,
    });
  }

  return result.sort((left, right) =>
    left.title.localeCompare(right.title, "ru", { sensitivity: "base" }),
  );
});

const storeCounterLabel = computed(() =>
  loadingStore.value
    ? "..."
    : String(storeTotal.value ?? storePlugins.value.length),
);

const sidebarTreeGroups = computed<TreeNodeGroup[]>(() => {
  if (activeTab.value === "installed") {
    const grouped = new Map<string, TreeNodeItem[]>();
    const usageRegistry = pluginUsageRegistry.value;

    for (const plugin of installedPlugins.value) {
      const usage = usageRegistry.get(plugin.id);
      const groups =
        usage && usage.groupLabels.size
          ? Array.from(usage.groupLabels.values())
          : ["Без группы"];

      for (const groupLabel of groups) {
        const list = grouped.get(groupLabel) || [];
        list.push({
          id: `installed:${groupLabel}:${plugin.id}`,
          label: plugin.title,
          pluginId: plugin.id,
          disabled: false,
        });
        grouped.set(groupLabel, list);
      }
    }

    return Array.from(grouped.entries())
      .map(([label, items], index) => ({
        id: `installed-group:${index}:${label}`,
        label,
        items: items.sort((left, right) =>
          left.label.localeCompare(right.label, "ru", { sensitivity: "base" }),
        ),
      }))
      .sort((left, right) =>
        left.label.localeCompare(right.label, "ru", { sensitivity: "base" }),
      );
  }

  if (activeTab.value === "store") {
    const grouped = new Map<string, TreeNodeItem[]>();
    for (const plugin of storePlugins.value) {
      const groupLabel = plugin.source || "other";
      const list = grouped.get(groupLabel) || [];
      list.push({
        id: `store:${groupLabel}:${plugin.id}`,
        label: plugin.title,
        pluginId: plugin.openPluginId || plugin.id,
        disabled: !plugin.installed,
      });
      grouped.set(groupLabel, list);
    }

    return Array.from(grouped.entries())
      .map(([label, items], index) => ({
        id: `store-group:${index}:${label}`,
        label,
        items: items.sort((left, right) =>
          left.label.localeCompare(right.label, "ru", { sensitivity: "base" }),
        ),
      }))
      .sort((left, right) =>
        left.label.localeCompare(right.label, "ru", { sensitivity: "base" }),
      );
  }

  return [
    {
      id: "settings-group:general",
      label: "Global settings",
      items: [
        {
          id: "settings:runtime",
          label: "Plugin runtime",
          pluginId: "",
          disabled: true,
        },
        {
          id: "settings:security",
          label: "Plugin security",
          pluginId: "",
          disabled: true,
        },
      ],
    },
  ];
});

onMounted(() => {
  void Promise.all([loadInstalledPlugins(), loadStorePlugins()]);
});

watch(
  () => activeTab.value,
  (tab) => {
    activeTreeNodeId.value = "";
    if (tab === "installed") {
      void loadInstalledPlugins();
      return;
    }
    if (tab === "store") {
      void loadStorePlugins();
    }
  },
);

function handleTreeNodeClick(item: TreeNodeItem): void {
  activeTreeNodeId.value = item.id;
  if (item.disabled) return;
  if (!item.pluginId) return;
  openPlugin(item.pluginId);
}

function isInstallingStorePlugin(pluginId: string): boolean {
  return Boolean(installingStorePlugins[pluginId]);
}

async function installStorePlugin(plugin: StorePlugin): Promise<void> {
  const storePluginId = String(plugin.id || "").trim();
  if (!storePluginId) return;
  if (isInstallingStorePlugin(storePluginId)) return;

  installingStorePlugins[storePluginId] = true;
  storeActionStatus.value = "idle";
  storeActionMessage.value = "";

  try {
    const response = await requestJson(
      `/api/v1/store/${encodeURIComponent(storePluginId)}/install`,
      { method: "POST" },
    );

    const responseRecord = asRecord(response);
    const installedPlugin = asRecord(responseRecord?.plugin);
    const runtimePluginId =
      asNonEmptyString(installedPlugin?.id) ||
      asNonEmptyString(installedPlugin?.name);

    if (runtimePluginId) {
      try {
        await requestJson(
          `/api/v1/plugins/${encodeURIComponent(runtimePluginId)}/load`,
          { method: "POST" },
        );
      } catch {
        // Loading can fail on plugin-specific runtime dependencies.
      }
    }

    await Promise.all([loadInstalledPlugins(), loadStorePlugins()]);

    storeActionStatus.value = "success";
    storeActionMessage.value =
      asNonEmptyString(responseRecord?.message) ||
      `Плагин '${plugin.title}' установлен`;
  } catch (error: unknown) {
    storeActionStatus.value = "error";
    storeActionMessage.value = `Не удалось установить '${plugin.title}': ${messageFromError(error)}`;
  } finally {
    delete installingStorePlugins[storePluginId];
  }
}

function setActiveTab(tab: PluginPanelTab): void {
  emit("setTab", tab);
}

function openPlugin(pluginId: string): void {
  const normalizedId = String(pluginId || "").trim();
  if (!normalizedId) return;
  emit("openPlugin", normalizedId);
}

function handleInstallZipClick(): void {
  if (installActionsDisabled) return;
  zipInputRef.value?.click();
}

function handleZipInputChange(event: Event): void {
  const target = event.target as HTMLInputElement | null;
  if (!target?.files?.length) return;
  target.value = "";
}

function handleInstallGithubLinkClick(): void {
  if (installActionsDisabled) return;
  githubInstallModal.open = true;
  githubInstallModal.link = "";
  githubInstallModal.message = "";
  githubInstallModal.status = "idle";
  void nextTick(() => {
    githubInputRef.value?.focus();
  });
}

function closeGithubInstallModal(): void {
  githubInstallModal.open = false;
}

function extractGithubRepoPath(link: string): string {
  const trimmed = String(link || "").trim();
  if (!trimmed) return "";

  const normalizedLink = trimmed.startsWith("http")
    ? trimmed
    : `https://${trimmed}`;

  try {
    const parsed = new URL(normalizedLink);
    const hostname = parsed.hostname.toLowerCase();
    if (hostname !== "github.com" && hostname !== "www.github.com") {
      return "";
    }

    const segments = parsed.pathname.split("/").filter(Boolean);
    if (segments.length < 2) return "";

    const owner = String(segments[0] || "").trim();
    const rawRepo = String(segments[1] || "").trim();
    const repo = rawRepo.endsWith(".git")
      ? rawRepo.slice(0, rawRepo.length - 4)
      : rawRepo;
    if (!owner || !repo) return "";

    return `${owner}/${repo}`;
  } catch {
    return "";
  }
}

function checkGithubLink(): boolean {
  const repoPath = extractGithubRepoPath(githubInstallModal.link);
  if (!repoPath) {
    githubInstallModal.status = "error";
    githubInstallModal.message =
      "Ссылка не распознана. Используйте формат github.com/owner/repo";
    return false;
  }

  githubInstallModal.status = "ok";
  githubInstallModal.message = `Репозиторий найден: ${repoPath}`;
  return true;
}

function submitGithubInstall(): void {
  if (!checkGithubLink()) return;
  closeGithubInstallModal();
}
</script>
