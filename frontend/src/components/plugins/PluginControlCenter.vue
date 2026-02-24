<template>
  <section class="plugins-panel-layout">
    <aside class="sidebar plugins-panel-nav">
      <div
        id="sidebar-particles"
        class="sidebar-particles"
        aria-hidden="true"
      ></div>

      <div class="sidebar-content plugins-panel-sidebar-content">
        <header class="plugins-panel-brand">
          <img :src="EMBLEM_SRC" alt="" aria-hidden="true" />
          <div>
            <p class="plugins-panel-brand-kicker">Oko Platform</p>
            <h1>Plugin Center</h1>
            <p class="plugins-panel-brand-note">
              Manage extensions and capabilities
            </p>
          </div>
        </header>

        <nav
          class="plugins-panel-nav-links"
          aria-label="Разделы панели плагинов"
        >
          <button
            class="plugins-panel-nav-link"
            :class="{ active: activeTab === 'installed' }"
            type="button"
            :aria-current="activeTab === 'installed' ? 'page' : undefined"
            @click="setActiveTab('installed')"
          >
            <Package class="ui-icon" />
            <span>Установленные плагины</span>
            <strong>{{ installedPlugins.length }}</strong>
          </button>

          <button
            class="plugins-panel-nav-link"
            :class="{ active: activeTab === 'store' }"
            type="button"
            :aria-current="activeTab === 'store' ? 'page' : undefined"
            @click="setActiveTab('store')"
          >
            <Store class="ui-icon" />
            <span>Store</span>
            <strong>soon</strong>
          </button>

          <button
            class="plugins-panel-nav-link"
            :class="{ active: activeTab === 'settings' }"
            type="button"
            :aria-current="activeTab === 'settings' ? 'page' : undefined"
            @click="setActiveTab('settings')"
          >
            <Settings class="ui-icon" />
            <span>Settings</span>
            <strong>beta</strong>
          </button>
        </nav>

        <section
          class="plugins-install-actions"
          aria-label="Установка плагинов"
        >
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
            @click="handleInstallZipClick"
          >
            <FileArchive class="ui-icon" />
            <span>Установить ZIP</span>
          </button>

          <button
            class="plugins-install-btn"
            type="button"
            @click="handleInstallGithubLinkClick"
          >
            <Github class="ui-icon" />
            <span>Установить GitHub link</span>
          </button>
        </section>

        <button
          class="ghost plugins-panel-back"
          type="button"
          title="Вернуться в Dashboard"
          aria-label="Вернуться в Dashboard"
          @click="emitClose"
        >
          <ArrowLeft class="ui-icon" />
          <span>Назад в Dashboard</span>
        </button>
      </div>
    </aside>

    <main class="panel plugins-panel-main">
      <HeroGlassTabsShell :emblem-src="EMBLEM_SRC">
        <nav
          class="hero-page-tabs has-logo-tile plugins-main-tabs"
          role="tablist"
          aria-label="Вкладки панели плагинов"
        >
          <div class="hero-logo-square" aria-hidden="true">
            <img :src="EMBLEM_SRC" alt="" />
          </div>

          <button
            class="hero-page-tab-btn"
            :class="{ active: activeTab === 'installed' }"
            type="button"
            role="tab"
            :aria-selected="activeTab === 'installed'"
            @click="setActiveTab('installed')"
          >
            <Package class="ui-icon hero-page-tab-icon" />
            <span class="hero-page-tab-label">Установленные плагины</span>
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
            <span class="hero-page-tab-label">Store</span>
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
            <span class="hero-page-tab-label">Settings</span>
          </button>
        </nav>

        <template #actions>
          <button
            class="ghost plugins-panel-close"
            type="button"
            title="Закрыть"
            aria-label="Закрыть"
            @click="emitClose"
          >
            <X class="ui-icon" />
          </button>
        </template>
      </HeroGlassTabsShell>

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
          <p>Каталог плагинов будет добавлен в следующем этапе.</p>
        </header>
        <section class="plugins-main-tile-wrap">
          <div class="plugins-empty-state">
            <h3>Store будет добавлен позже</h3>
            <p>Раздел оставлен пустым по текущему ТЗ.</p>
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
    </main>
  </section>

  <BaseModal
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
      <button
        class="plugins-github-check-btn"
        type="button"
        @click="checkGithubLink"
      >
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
  </BaseModal>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from "vue";
import {
  ArrowLeft,
  FileArchive,
  Github,
  Package,
  Settings,
  Store,
  X,
} from "lucide-vue-next";
import BaseModal from "@/components/primitives/BaseModal.vue";
import HeroGlassTabsShell from "@/components/primitives/HeroGlassTabsShell.vue";
import { useDashboardStore } from "@/stores/dashboardStore";

type PluginPanelTab = "installed" | "store" | "settings";

interface InstalledPlugin {
  id: string;
  title: string;
  serviceCount: number;
  elementsCount: number;
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
  close: [];
  setTab: [tab: PluginPanelTab];
  openPlugin: [pluginId: string];
}>();

const dashboard = useDashboardStore();
const { EMBLEM_SRC, config, initSidebarParticles } = dashboard;
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

const installedPlugins = computed<InstalledPlugin[]>(() => {
  const registry = new Map<
    string,
    {
      id: string;
      title: string;
      serviceIds: Set<string>;
      elementsCount: number;
    }
  >();

  for (const group of config.value?.groups || []) {
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

          const existing = registry.get(pluginId) || {
            id: pluginId,
            title: pluginId,
            serviceIds: new Set<string>(),
            elementsCount: 0,
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

          registry.set(pluginId, existing);
        }
      }
    }
  }

  return Array.from(registry.values())
    .map((entry) => ({
      id: entry.id,
      title: entry.title,
      serviceCount: entry.serviceIds.size,
      elementsCount: entry.elementsCount,
    }))
    .sort((left, right) =>
      left.title.localeCompare(right.title, "ru", { sensitivity: "base" }),
    );
});

function setActiveTab(tab: PluginPanelTab): void {
  emit("setTab", tab);
}

function emitClose(): void {
  emit("close");
}

function openPlugin(pluginId: string): void {
  const normalizedId = String(pluginId || "").trim();
  if (!normalizedId) return;
  emit("openPlugin", normalizedId);
}

function handleInstallZipClick(): void {
  zipInputRef.value?.click();
}

function handleZipInputChange(event: Event): void {
  const target = event.target as HTMLInputElement | null;
  if (!target?.files?.length) return;
  target.value = "";
}

function handleInstallGithubLinkClick(): void {
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

onMounted(() => {
  void initSidebarParticles();
});
</script>
