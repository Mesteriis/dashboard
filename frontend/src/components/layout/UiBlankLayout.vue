<template>
  <!-- Корневой каркас страницы -->
  <main
      id="layout-shell"
      class="app-shell blank-page"
      :class="{
        'sidebar-hidden': !hasSidebar || sidebarHidden,
        'no-header': !hasHeader
      }"
      :data-layout-api-version="layoutApiVersion"
  >
    <!-- Левый сайдбар -->
    <aside
        v-show="hasSidebar && !sidebarHidden"
        id="layout-sidebar"
        class="sidebar blank-sidebar"
        :class="{ 'is-hidden': !hasSidebar || sidebarHidden }"
    >
      <div
          v-if="sidebarParticlesId"
          :id="sidebarParticlesId"
          class="sidebar-particles"
          aria-hidden="true"
      ></div>

      <div class="sidebar-content">
        <!-- Логотип / бренд -->
        <section id="layout-sidebar-brand" class="blank-sidebar-logo" aria-label="Бренд">
          <img v-if="emblemSrc" :src="emblemSrc" class="logo-emblem" alt="" aria-hidden="true"/>
          <div class="logo-text">
            <span class="logo-name">Око</span>
            <span class="logo-slogan">Your Infrastructure in Sight</span>
          </div>
          <UiIconButton
              v-if="hasSidebar && !sidebarHidden"
              button-class="logo-toggle-btn"
              :title="sidebarViewToggleTitle"
              :aria-label="sidebarViewToggleTitle"
              @click="handleSidebarToggle"
          >
            <PanelLeftClose class="ui-icon"/>
          </UiIconButton>
        </section>
        <!-- Основная навигация -->
        <section id="sidebar-content-mid">
          <slot name="sidebar-mid"/>
        </section>
        <section id="layout-sidebar-nav" class="blank-sidebar-main" aria-label="Навигация"/>

        <!-- Раскрывающаяся нижняя секция -->
        <section
            v-if="sidebarBottomVisible"
            id="layout-sidebar-details"
            class="blank-sidebar-accordion"
            :class="{ 'is-open': isSidebarBottomOpen }"
        >
          <div
              :id="sidebarBottomPanelId"
              class="blank-sidebar-accordion__panel"
              role="region"
              :aria-label="sidebarBottomAccordionLabel"
              :aria-hidden="!isSidebarBottomOpen"
          />

          <button
              type="button"
              class="blank-sidebar-accordion__trigger"
              :aria-expanded="isSidebarBottomOpen"
              :aria-controls="sidebarBottomPanelId"
              @click="toggleSidebarBottom"
          >
            <span>{{ sidebarBottomAccordionLabel }}</span>
            <span class="ui-icon blank-sidebar-accordion__trigger-icon" aria-hidden="true">
              {{ isSidebarBottomOpen ? "▴" : "▾" }}
            </span>
          </button>
        </section>
      </div>
    </aside>

    <!-- Основная область -->
    <div id="layout-main" class="blank-main">
      <!-- ① Шапка: вкладки + панель управления -->
      <header v-if="hasHeader" id="layout-header" class="blank-main-header hero-layout">
        <UiIconButton
            v-if="showSidebarToggle"
            button-class="sidebar-toggle-btn"
            :title="sidebarViewToggleTitle"
            :aria-label="sidebarViewToggleTitle"
            @click="handleSidebarToggle"
        >
          <PanelRightOpen class="ui-icon sidebar-toggle-icon"/>
        </UiIconButton>

        <UiHeroGlassTabsShell
            id="layout-header-tabs"
            class="hero-title-panel"
            :emblem-src="emblemSrc"
        >
          <div class="blank-header-main"/>
        </UiHeroGlassTabsShell>

        <UiHeroControlsAccordion
            v-if="$slots.drawer"
            :drawer-id="headerPanelDrawerId"
            :storage-key="resolvedHeaderPanelStorageKey"
            :initial-open="headerPanelInitiallyOpen"
            @open-change="handleHeaderPanelOpenChange"
        >
          <template #drawer />
        </UiHeroControlsAccordion>

        <UiDropdownMenu
            class="hero-action-menu align-right"
            aria-label="Системное меню"
            :items="systemActions"
            :show-caret="false"
            trigger-class="hero-icon-btn hero-accordion-action hero-system-menu-trigger"
            item-class="hero-system-menu-item"
            @action="handleSystemAction"
        >
          <template #trigger>
            <Lock class="ui-icon hero-action-icon"/>
          </template>
        </UiDropdownMenu>
      </header>

      <!-- ② Основной контент -->
      <section
          id="layout-canvas"
          class="blank-canvas"
          :aria-label="contentLabel"
          :style="layoutCanvasStyle"
      >
        <div class="blank-canvas-bg" aria-hidden="true"/>
      </section>

    </div>
  </main>
</template>

<script setup lang="ts">
import {computed, ref, useSlots, watch} from "vue";
import {useRoute} from "vue-router";
import {Lock, PanelLeftClose, PanelRightOpen} from "lucide-vue-next";
import UiHeroGlassTabsShell from "@/components/layout/UiHeroGlassTabsShell.vue";
import UiHeroControlsAccordion from "@/components/layout/UiHeroControlsAccordion.vue";
import UiIconButton from "@/ui/actions/UiIconButton.vue";
import UiDropdownMenu from "@/primitives/overlays/UiDropdownMenu.vue";
import {openPleiadOverlay} from "@/app/navigation/nav";
import {getRuntimeProfile} from "@/features/services/desktopRuntime";
import {useDashboardStore} from "@/features/stores/dashboardStore";
import {EMBLEM_SRC} from "@/features/stores/dashboard/storeConstants";

let sidebarBottomPanelCounter = 0;

const props = withDefaults(
    defineProps<{
      emblemSrc: string;
      layoutMode?: "default" | "no-sidebar" | "content-only";
      sidebarHidden?: boolean;
      sidebarParticlesId?: string;
      sidebarBottomAccordionLabel?: string;
      sidebarBottomAccordionInitiallyOpen?: boolean;
      sidebarBottomVisible?: boolean;
      contentLabel?: string;
      headerPanelActive?: boolean;
      headerPanelDrawerId?: string;
      headerPanelStorageKey?: string;
      headerPanelInitiallyOpen?: boolean | null;
      layoutApiVersion?: "v1";
    }>(),
    {
      layoutMode: "default",
      sidebarHidden: false,
      sidebarParticlesId: "",
      sidebarBottomAccordionLabel: "Sidebar details",
      sidebarBottomAccordionInitiallyOpen: true,
      sidebarBottomVisible: false,
      contentLabel: "Основной контент",
      headerPanelActive: false,
      headerPanelDrawerId: "layout-header-controls-drawer",
      headerPanelStorageKey: "",
      headerPanelInitiallyOpen: null,
      layoutApiVersion: "v1",
    },
);

const emit = defineEmits<{
  "header-panel-open-change": [value: boolean];
}>();

const route = useRoute();
const dashboard = useDashboardStore();
const {openSettingsPanel, sidebarView, sidebarViewToggleTitle, toggleSidebarView} = dashboard;

// ── Системное меню ────────────────────────────────────────────────────────

type SystemActionId = "settings" | "kiosk" | "pleiad_lock" | "exit";

const systemActions: Array<{ id: SystemActionId; label: string; danger?: boolean }> = [
  {id: "settings", label: "Настройки"},
  {id: "kiosk", label: "Режим киоска"},
  {id: "pleiad_lock", label: "Заблокировать"},
  {id: "exit", label: "Выход", danger: true},
];

async function toggleKioskMode(): Promise<void> {
  if (typeof document === "undefined") return;
  try {
    if (document.fullscreenElement) {
      await document.exitFullscreen();
    } else {
      await document.documentElement.requestFullscreen();
    }
  } catch {
    // ignore
  }
}

async function exitApp(): Promise<void> {
  try {
    if (getRuntimeProfile().desktop) {
      const {getCurrentWindow} = await import("@tauri-apps/api/window");
      await getCurrentWindow().close();
      return;
    }
  } catch {
    // fall through
  }
  if (typeof window !== "undefined") window.close();
}

function handleSystemAction(actionId: string): void {
  switch (actionId) {
    case "settings":
      openSettingsPanel();
      break;
    case "kiosk":
      void toggleKioskMode();
      break;
    case "pleiad_lock":
      void openPleiadOverlay("route");
      break;
    case "exit":
      void exitApp();
      break;
  }
}

const isSidebarBottomOpen = ref(Boolean(props.sidebarBottomAccordionInitiallyOpen));
const sidebarBottomPanelId = `blank-sidebar-bottom-panel-${++sidebarBottomPanelCounter}`;

const hasSidebar = computed(() => props.layoutMode !== "no-sidebar" && props.layoutMode !== "content-only");
const hasHeader = computed(() => props.layoutMode !== "content-only");
const showSidebarToggle = computed(() => hasSidebar.value && props.sidebarHidden);

const resolvedHeaderPanelStorageKey = computed(() => {
  const customKey = String(props.headerPanelStorageKey || "").trim();
  if (customKey) return customKey;
  const rawPath = String(route.path || "/").trim();
  const normalizedPath =
      rawPath.length > 1 && rawPath.endsWith("/") ? rawPath.slice(0, -1) : rawPath;
  return `oko:hero-controls-open:${normalizedPath || "/"}`;
});

const layoutCanvasStyle = computed(() => {
  const src = props.emblemSrc || EMBLEM_SRC;
  return {
    "--blank-canvas-emblem-url": `url('${src}')`,
  };
});

watch(
    () => props.sidebarBottomVisible,
    (visible) => {
      if (!visible) isSidebarBottomOpen.value = false;
      else isSidebarBottomOpen.value = Boolean(props.sidebarBottomAccordionInitiallyOpen);
    },
);

function toggleSidebarBottom(): void {
  isSidebarBottomOpen.value = !isSidebarBottomOpen.value;
}

function handleSidebarToggle(): void {
  const before = sidebarView.value;
  toggleSidebarView();
  if (sidebarView.value !== before) return;
  sidebarView.value = before === "hidden" ? "detailed" : "hidden";
}

function handleHeaderPanelOpenChange(value: boolean): void {
  emit("header-panel-open-change", value);
}

// ── Validation ───────────────────────────────────────────────────────────────

if (import.meta.env.DEV) {
  const $slots = useSlots();
  const hasSidebarSlot = Boolean($slots["sidebar-mid"]);
  const hasHeaderSlot = Boolean($slots.default);

  if (props.layoutMode === "default") {
    if (!hasSidebarSlot && !hasHeaderSlot) {
      throw new Error(
        "[UiBlankLayout] layoutMode=\"default\" requires at least one slot: " +
        "\"sidebar-mid\" or default slot for header content. " +
        "Either provide content in these slots or use a different layoutMode.",
      );
    }
  }

  if (props.layoutMode === "no-sidebar") {
    if (hasSidebarSlot) {
      throw new Error(
        "[UiBlankLayout] layoutMode=\"no-sidebar\" does not support \"sidebar-mid\" slot. " +
        "Remove the slot or use layoutMode=\"default\".",
      );
    }
  }

  if (props.layoutMode === "content-only") {
    if (hasSidebarSlot) {
      throw new Error(
        "[UiBlankLayout] layoutMode=\"content-only\" does not support \"sidebar-mid\" slot. " +
        "Remove the slot or use a different layoutMode.",
      );
    }
    if (hasHeaderSlot) {
      throw new Error(
        "[UiBlankLayout] layoutMode=\"content-only\" does not support default slot (header content). " +
        "Remove the slot or use a different layoutMode.",
      );
    }
  }
}


</script>

<style scoped>
/* ── Корневая сетка страницы ─────────────────────────────────────────── */

.blank-page {
  grid-template-columns: 420px minmax(0, 1fr);
  height: calc(100vh - var(--desktop-drag-strip, 0px));
  min-height: unset;
  align-items: stretch;
}

.blank-page.sidebar-hidden {
  grid-template-columns: minmax(0, 1fr);
}

.blank-page.no-header {
  grid-template-rows: minmax(0, 1fr);
}

.blank-page.no-header .blank-main {
  grid-template-rows: minmax(0, 1fr);
}

.blank-page.no-header .blank-canvas {
  height: 100%;
}

.blank-sidebar.is-hidden {
  display: none;
}

/* ── Основная колонка ────────────────────────────────────────────────── */

.blank-main {
  position: relative;
  isolation: isolate;
  min-height: 0;
  height: 100%;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 10px;
  overflow: hidden;
}

/* ── Кнопка показа панели ───────────────────────────────────────────── */

.sidebar-toggle-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: var(--ui-radius);
  background: transparent;
  border: 1px solid transparent;
  color: rgba(200, 230, 255, 0.9);
  cursor: pointer;
  transition: all 170ms ease;
}

.sidebar-toggle-btn:hover {
  background: rgba(30, 60, 90, 0.4);
  border-color: rgba(120, 183, 218, 0.2);
}

.sidebar-toggle-btn:focus-visible {
  outline: none;
  border-color: rgba(166, 225, 255, 0.4);
  box-shadow: 0 0 0 2px rgba(103, 177, 219, 0.2);
}

.sidebar-toggle-emblem {
  width: 22px;
  height: 22px;
  object-fit: contain;
  border-radius: 4px;
}

.sidebar-toggle-icon {
  width: 16px;
  height: 16px;
}

/* ── ① Шапка (#layout-header) ───────────────────────────────────────── */

.blank-main-header {
  position: relative;
  z-index: 50;
  display: flex;
  align-items: center;
  gap: 8px;
}

.blank-main-header > :deep(.hero-title-panel) {
  flex: 1;
  height: 100%;
}

.blank-main-header .sidebar-toggle-btn {
  flex-shrink: 0;
}

.blank-main-header .hero-action-menu {
  flex-shrink: 0;
}

.blank-main-header :deep(.hero-glass-tabs-shell) {
  position: relative;
  z-index: 40;
  overflow: visible;
}

.blank-main-header :deep(.hero-action-menu) {
  z-index: 240;
}

.blank-main-header :deep(.hero-control-panel--menu .ui-menu__list) {
  z-index: 280;
}

.blank-header-main {
  display: contents;
}

/* ── ② Контент (#layout-canvas) ─────────────────────────────────────── */

.blank-canvas {
  --blank-canvas-pad: clamp(14px, 2vw, 24px);
  position: relative;
  z-index: 1;
  height: 100%;
  border: 1px solid rgba(89, 144, 166, 0.18);
  border-radius: var(--ui-radius);
  background-color: transparent;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
  padding: var(--blank-canvas-pad);
  overflow: hidden;
  display: grid;
  align-content: start;
  gap: 10px;
}

.blank-canvas::before {
  content: "";
  position: absolute;
  inset: 0;
  padding: var(--blank-canvas-pad);
  background-image: var(--blank-canvas-emblem-url);
  background-repeat: no-repeat;
  background-position: center 52%;
  background-origin: content-box;
  background-size: 50% auto;
  opacity: 0.1;
  mix-blend-mode: screen;
  pointer-events: none;
  z-index: 0;
}

.blank-canvas > *:not(.blank-canvas-bg) {
  position: relative;
  z-index: 1;
}

.blank-canvas-bg {
  position: absolute;
  inset: calc(-1 * var(--blank-canvas-pad));
  display: grid;
  place-items: center;
  pointer-events: none;
  z-index: 0;
}

.blank-canvas-top,
.blank-canvas-main,
.blank-canvas-bottom {
  min-width: 0;
  min-height: 0;
}

/* ── Сайдбар ─────────────────────────────────────────────────────────── */

.blank-sidebar {
  min-height: 0;
}

.blank-sidebar .sidebar-content {
  display: flex;
  flex-direction: column;
  min-height: 0;
  gap: 10px;
}

.blank-sidebar-logo {
  flex: 0 0 auto;
  min-height: 0;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 14px;
}

.logo-emblem {
  width: 42px;
  height: 42px;
  object-fit: contain;
  border-radius: var(--ui-radius);
}

.logo-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
}

.logo-name {
  font-size: 1.25rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: rgba(220, 240, 255, 0.95);
}

.logo-slogan {
  font-size: 0.7rem;
  letter-spacing: 0.06em;
  color: rgba(160, 200, 230, 0.7);
  text-transform: uppercase;
}

.logo-toggle-btn {
  margin-inline-start: auto;
  padding: 6px;
  border-radius: var(--ui-radius);
  background: transparent;
  border: 1px solid transparent;
  color: rgba(160, 200, 230, 0.7);
  cursor: pointer;
  transition: all 170ms ease;
}

.logo-toggle-btn:hover {
  background: rgba(30, 60, 90, 0.4);
  border-color: rgba(120, 183, 218, 0.2);
  color: rgba(200, 230, 255, 0.9);
}

.logo-toggle-btn:focus-visible {
  outline: none;
  border-color: rgba(166, 225, 255, 0.4);
  box-shadow: 0 0 0 2px rgba(103, 177, 219, 0.2);
}

.logo-toggle-btn .ui-icon {
  width: 18px;
  height: 18px;
}

.blank-sidebar-main {
  flex: 1 1 auto;
  min-height: 0;
  overflow: hidden;
}

.blank-sidebar-accordion {
  flex: 0 0 auto;
  min-height: 0;
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto;
  gap: 8px;
}

.blank-sidebar-accordion__panel {
  overflow: hidden;
  max-height: 0;
  opacity: 0;
  transform: translateY(10px);
  border-radius: var(--ui-radius);
  border: 1px solid transparent;
  background: linear-gradient(146deg, rgba(15, 34, 51, 0.5), rgba(10, 24, 40, 0.36));
  padding: 0 10px;
  transition: max-height 230ms ease,
  opacity 170ms ease,
  transform 230ms ease,
  border-color 230ms ease,
  padding 230ms ease;
}

.blank-sidebar-accordion.is-open .blank-sidebar-accordion__panel {
  max-height: min(42vh, 340px);
  opacity: 1;
  transform: translateY(0);
  border-color: rgba(120, 183, 218, 0.28);
  padding: 10px;
  overflow-y: auto;
}

.blank-sidebar-accordion__trigger {
  width: 100%;
  border: 1px solid rgba(110, 171, 208, 0.28);
  border-radius: var(--ui-radius);
  background: linear-gradient(146deg, rgba(20, 45, 68, 0.56), rgba(12, 30, 48, 0.45));
  color: rgba(220, 237, 250, 0.95);
  padding: 9px 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 0.82rem;
  letter-spacing: 0.03em;
  cursor: pointer;
  transition: border-color 170ms ease,
  box-shadow 170ms ease,
  background 170ms ease;
}

.blank-sidebar-accordion__trigger:hover {
  border-color: rgba(157, 216, 250, 0.52);
  background: linear-gradient(146deg, rgba(30, 63, 93, 0.58), rgba(17, 41, 65, 0.52));
}

.blank-sidebar-accordion__trigger:focus-visible {
  outline: none;
  border-color: rgba(166, 225, 255, 0.65);
  box-shadow: 0 0 0 3px rgba(103, 177, 219, 0.25);
}

.blank-sidebar-accordion__trigger-icon {
  transition: transform 220ms ease;
  transform: rotate(180deg);
}

.blank-sidebar-accordion.is-open .blank-sidebar-accordion__trigger-icon {
  transform: rotate(0deg);
}
</style>
