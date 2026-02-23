<template>
  <div
    class="shell"
    :class="{ 'shell-desktop': desktopShell }"
  >
    <div
      v-if="desktopShell"
      class="desktop-window-drag-strip"
      data-tauri-drag-region
      aria-hidden="true"
    ></div>
    <img
      v-if="!isPleiadRoute"
      class="center-emblem"
      :src="EMBLEM_SRC"
      alt=""
      aria-hidden="true"
    />

    <PleiadExperience v-if="isPleiadRoute" mode="route" @close="closePleiadRoute" />

    <template v-else>
      <div class="app-shell" :class="{ 'sidebar-hidden': isSidebarHidden }">
        <DashboardSidebarView v-if="!isSidebarHidden" />
        <DashboardMainView />
      </div>

      <LanHostModal v-if="lanHostModal.open" />
      <IframeModal v-if="iframeModal.open" />
      <ItemEditorModal v-if="itemEditor.open" />
      <DashboardSettingsModal v-if="settingsPanel.open" />
      <CommandPaletteModal v-if="commandPaletteOpen" />
    </template>

    <div v-if="screensaverVisible && !isPleiadRoute" class="pleiad-overlay-backdrop">
      <PleiadExperience mode="screensaver" @close="hideScreensaver" />
    </div>

    <div
      v-if="agentAuraDemoVisible && !isPleiadRoute"
      class="agent-aura-overlay-backdrop"
      @click.self="hideAgentAuraDemo"
    >
      <section
        class="agent-aura-overlay-panel"
        role="dialog"
        aria-modal="true"
        aria-label="Agent Aura FX demo"
      >
        <header class="agent-aura-overlay-head">
          <div>
            <p>Visual Playground</p>
            <h3>Agent Aura FX</h3>
          </div>
          <button
            class="agent-aura-overlay-close"
            type="button"
            aria-label="Close Agent Aura FX"
            @click="hideAgentAuraDemo"
          >
            Close
          </button>
        </header>
        <AgentAuraFxDemo />
      </section>
    </div>
  </div>
</template>

<script setup>
import {
  computed,
  defineAsyncComponent,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from "vue";
import PleiadExperience from "./components/pleiad/PleiadExperience.vue";
import { useIdleScreensaver } from "./composables/useIdleScreensaver.js";
import DashboardMainView from "./views/DashboardMainView.vue";
import DashboardSidebarView from "./views/DashboardSidebarView.vue";
import { AGENT_AURA_DEMO_OPEN_EVENT } from "./services/agentAuraNavigation.js";
import { isDesktopShell } from "./services/desktopRuntime.js";
import {
  PLEIAD_OPEN_EVENT,
  isPleiadPath,
  normalizePathname,
  resolvePleiadPath,
  resolveShellPath,
} from "./services/pleiadNavigation.js";
import { useDashboardStore } from "./stores/dashboardStore.js";

const loadLanHostModal = () => import("./components/modals/LanHostModal.vue");
const loadIframeModal = () => import("./components/modals/IframeModal.vue");
const loadItemEditorModal = () =>
  import("./components/modals/ItemEditorModal.vue");
const loadDashboardSettingsModal = () =>
  import("./components/modals/DashboardSettingsModal.vue");
const loadCommandPaletteModal = () =>
  import("./components/modals/CommandPaletteModal.vue");
const loadAgentAuraFxDemo = () =>
  import("./components/agents/AgentAuraFxDemo.vue");
const loadIndicatorTabPanel = () =>
  import("./components/main/IndicatorTabPanel.vue");
const loadLanPageView = () => import("./components/main/LanPageView.vue");

const LanHostModal = defineAsyncComponent(loadLanHostModal);
const IframeModal = defineAsyncComponent(loadIframeModal);
const ItemEditorModal = defineAsyncComponent(loadItemEditorModal);
const DashboardSettingsModal = defineAsyncComponent(loadDashboardSettingsModal);
const CommandPaletteModal = defineAsyncComponent(loadCommandPaletteModal);
const AgentAuraFxDemo = defineAsyncComponent(loadAgentAuraFxDemo);

const dashboard = useDashboardStore();
const {
  EMBLEM_SRC,
  closeCommandPalette,
  closeSettingsPanel,
  commandPaletteOpen,
  iframeModal,
  isSidebarHidden,
  itemEditor,
  lanHostModal,
  openSettingsPanel,
  settingsPanel,
  toggleCommandPalette,
} = dashboard;
const desktopShell = isDesktopShell();
const currentPathname = ref(
  normalizePathname(globalThis.location?.pathname || "/"),
);
const currentSearch = ref(String(globalThis.location?.search || ""));
const screensaverVisible = ref(false);
const agentAuraDemoVisible = ref(false);
const lastDashboardUrl = ref(resolveShellPath());
const isPleiadRoute = computed(() => isPleiadPath(currentPathname.value));

let idlePrefetchTimerId = 0;
let idlePrefetchCallbackId = 0;

useIdleScreensaver({
  timeoutMs: 10 * 60 * 1000,
  onIdle: () => {
    if (isPleiadRoute.value) return;
    screensaverVisible.value = true;
  },
  onActive: () => {
    if (!screensaverVisible.value) return;
    screensaverVisible.value = false;
  },
});

watch(
  () => [currentPathname.value, currentSearch.value],
  ([pathname, search]) => {
    if (isPleiadPath(pathname)) return;
    lastDashboardUrl.value = `${pathname}${search || ""}`;
  },
  { immediate: true },
);

watch(
  () => isPleiadRoute.value,
  (active) => {
    if (active) {
      screensaverVisible.value = false;
      agentAuraDemoVisible.value = false;
    }
  },
);

function runIdlePrefetch() {
  Promise.allSettled([
    loadLanHostModal(),
    loadIframeModal(),
    loadItemEditorModal(),
    loadDashboardSettingsModal(),
    loadCommandPaletteModal(),
    loadIndicatorTabPanel(),
    loadLanPageView(),
  ]);
}

function scheduleIdlePrefetch() {
  if ("requestIdleCallback" in window) {
    idlePrefetchCallbackId = window.requestIdleCallback(
      () => {
        idlePrefetchCallbackId = 0;
        runIdlePrefetch();
      },
      { timeout: 2000 },
    );
    return;
  }

  idlePrefetchTimerId = window.setTimeout(() => {
    idlePrefetchTimerId = 0;
    runIdlePrefetch();
  }, 1400);
}

function syncLocationFromWindow() {
  currentPathname.value = normalizePathname(window.location.pathname);
  currentSearch.value = String(window.location.search || "");
}

function buildPleiadUrl({ mode = "" } = {}) {
  const routePath = resolvePleiadPath();
  const query = new URLSearchParams();
  if (mode === "screensaver") {
    query.set("mode", "screensaver");
  }
  const rawQuery = query.toString();
  return `${routePath}${rawQuery ? `?${rawQuery}` : ""}`;
}

function openPleiadRoute({ mode = "" } = {}) {
  const targetUrl = buildPleiadUrl({ mode });
  const currentUrl = `${currentPathname.value}${currentSearch.value || ""}`;
  if (currentUrl === targetUrl) return;
  window.history.pushState(
    {
      okoRoute: "pleiad",
      from: lastDashboardUrl.value,
    },
    "",
    targetUrl,
  );
  syncLocationFromWindow();
}

function closePleiadRoute() {
  const fallbackUrl = lastDashboardUrl.value || resolveShellPath();

  if (
    window.history.length > 1 &&
    window.history.state &&
    window.history.state.okoRoute === "pleiad"
  ) {
    window.history.back();
    window.setTimeout(() => {
      if (!isPleiadPath(window.location.pathname)) return;
      window.history.replaceState(
        { okoRoute: "dashboard" },
        "",
        fallbackUrl,
      );
      syncLocationFromWindow();
    }, 0);
    return;
  }

  window.history.replaceState({ okoRoute: "dashboard" }, "", fallbackUrl);
  syncLocationFromWindow();
}

function hideScreensaver() {
  screensaverVisible.value = false;
}

function showAgentAuraDemo() {
  agentAuraDemoVisible.value = true;
}

function hideAgentAuraDemo() {
  agentAuraDemoVisible.value = false;
}

function handleGlobalShortcut(event) {
  if (event.key === "Escape" && agentAuraDemoVisible.value) {
    event.preventDefault();
    hideAgentAuraDemo();
    return;
  }

  if (event.key === "Escape" && screensaverVisible.value) {
    event.preventDefault();
    hideScreensaver();
    return;
  }

  if (event.key === "Escape" && isPleiadRoute.value) {
    event.preventDefault();
    closePleiadRoute();
    return;
  }

  const isShortcut =
    (event.metaKey || event.ctrlKey) &&
    !event.altKey &&
    !event.shiftKey &&
    event.key.toLowerCase() === "k";
  if (isShortcut) {
    event.preventDefault();
    toggleCommandPalette();
    return;
  }

  if (event.key === "Escape" && commandPaletteOpen.value) {
    event.preventDefault();
    closeCommandPalette();
    return;
  }

  if (event.key === "Escape" && settingsPanel.open) {
    event.preventDefault();
    closeSettingsPanel();
  }
}

function handleDesktopAction(event) {
  const action = String(event?.detail?.action || "");
  if (!action) return;

  if (action === "open-search") {
    toggleCommandPalette();
    return;
  }

  if (action === "open-settings") {
    openSettingsPanel();
  }
}

function handlePleiadOpenRequest(event) {
  hideAgentAuraDemo();
  const mode = String(event?.detail?.mode || "");
  if (mode === "screensaver") {
    screensaverVisible.value = true;
    return;
  }
  openPleiadRoute();
}

function handleAgentAuraOpenRequest() {
  if (isPleiadRoute.value) return;
  screensaverVisible.value = false;
  showAgentAuraDemo();
}

function handlePopstate() {
  syncLocationFromWindow();
}

onMounted(() => {
  syncLocationFromWindow();
  window.addEventListener("keydown", handleGlobalShortcut);
  window.addEventListener("oko:desktop-action", handleDesktopAction);
  window.addEventListener("popstate", handlePopstate);
  window.addEventListener(PLEIAD_OPEN_EVENT, handlePleiadOpenRequest);
  window.addEventListener(AGENT_AURA_DEMO_OPEN_EVENT, handleAgentAuraOpenRequest);
  scheduleIdlePrefetch();
});

onBeforeUnmount(() => {
  if (idlePrefetchTimerId) {
    window.clearTimeout(idlePrefetchTimerId);
    idlePrefetchTimerId = 0;
  }
  if (idlePrefetchCallbackId && "cancelIdleCallback" in window) {
    window.cancelIdleCallback(idlePrefetchCallbackId);
    idlePrefetchCallbackId = 0;
  }
  window.removeEventListener("keydown", handleGlobalShortcut);
  window.removeEventListener("oko:desktop-action", handleDesktopAction);
  window.removeEventListener("popstate", handlePopstate);
  window.removeEventListener(PLEIAD_OPEN_EVENT, handlePleiadOpenRequest);
  window.removeEventListener(
    AGENT_AURA_DEMO_OPEN_EVENT,
    handleAgentAuraOpenRequest,
  );
});
</script>
