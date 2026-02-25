<template>
  <!-- Корневой контейнер layout: общий каркас страницы -->
  <main
    class="app-shell blank-page"
    :class="{ 'sidebar-hidden': sidebarHidden }"
    :data-layout-api-version="layoutApiVersion"
  >
    <!-- Фоновый слой layout (декор/эффекты от родителя) -->
    <slot name="app.shell.background" />

    <!-- Левый сайдбар (скрывается при sidebarHidden) -->
    <aside v-if="!sidebarHidden" class="sidebar blank-sidebar">
      <!-- Контейнер для частиц/визуального эффекта в сайдбаре -->
      <div
        v-if="sidebarParticlesId"
        :id="sidebarParticlesId"
        class="sidebar-particles"
        aria-hidden="true"
      ></div>

      <div class="sidebar-content">
        <!-- Верх сайдбара: обычно логотип/бренд -->
        <section class="blank-sidebar-logo">
          <slot name="app.sidebar.top" />
        </section>

        <!-- Основная часть сайдбара: навигация/контент -->
        <section class="blank-sidebar-main">
          <slot name="app.sidebar.middle" />
        </section>

        <!-- Нижний блок сайдбара: сворачиваемая секция с доп. контентом -->
        <section
          v-if="hasSidebarBottomContent"
          class="blank-sidebar-accordion"
          :class="{ 'is-open': isSidebarBottomOpen }"
        >
          <!-- Панель аккордеона (контент снизу сайдбара) -->
          <div
            :id="sidebarBottomPanelId"
            class="blank-sidebar-accordion__panel"
            role="region"
            :aria-label="sidebarBottomAccordionLabel"
            :aria-hidden="!isSidebarBottomOpen"
          >
            <slot name="app.sidebar.bottom" />
          </div>

          <!-- Кнопка открытия/закрытия нижней панели -->
          <button
            type="button"
            class="blank-sidebar-accordion__trigger"
            :aria-expanded="isSidebarBottomOpen"
            :aria-controls="sidebarBottomPanelId"
            @click="toggleSidebarBottom"
          >
            <span>{{ sidebarBottomAccordionLabel }}</span>
            <span
              class="ui-icon blank-sidebar-accordion__trigger-icon"
              aria-hidden="true"
            >
              <slot name="sidebar-bottom-toggle-icon" :open="isSidebarBottomOpen">
                {{ isSidebarBottomOpen ? "▴" : "▾" }}
              </slot>
            </span>
          </button>
        </section>
      </div>
    </aside>

    <!-- Основная область страницы -->
    <section class="blank-main">
      <!-- Верхняя панель: табы/заголовок + панель действий -->
      <section class="blank-main-header hero-layout">
        <!-- Блок заголовка c табами и эмблемой -->
        <UiHeroGlassTabsShell class="hero-title-panel" :emblem-src="emblemSrc">
          <div class="blank-header-main">
            <!-- Левая часть header (опционально) -->
            <div v-if="hasHeaderLeft" class="blank-header-left">
              <slot name="app.header.left" />
            </div>
            <!-- Основные header tabs -->
            <div class="blank-header-tabs">
              <slot name="app.header.tabs" />
            </div>
          </div>
        </UiHeroGlassTabsShell>

        <!-- Правая панель управления (drawer/actions/footer) -->
        <aside
          class="panel hero-control-panel hero-control-panel--menu service-hero-controls"
          :class="{ active: headerPanelActive }"
        >
          <UiHeroControlsAccordion
            :drawer-id="headerPanelDrawerId"
            :storage-key="resolvedHeaderPanelStorageKey"
            :initial-open="headerPanelInitiallyOpen"
            @open-change="handleHeaderPanelOpenChange"
          >
            <!-- Триггер drawer: можно переопределить через slot -->
            <template #drawer>
              <slot name="app.header.panel.drawer">
                <!-- Fallback-кнопка переключения режима сайдбара -->
                <UiIconButton
                  button-class="hero-icon-btn hero-accordion-action"
                  :active="!isSidebarDetailed"
                  :title="sidebarViewToggleTitle"
                  :aria-label="sidebarViewToggleTitle"
                  @click="handleSidebarToggle"
                >
                  <FolderTree class="ui-icon hero-action-icon" />
                </UiIconButton>
              </slot>
            </template>

            <!-- Действия в header-панели -->
            <template #actions>
              <slot name="app.header.panel.actions" />
              <slot name="app.header.actions" />

              <!-- Dropdown-меню действий (из panel.menu или actions.menu) -->
              <div
                v-if="hasHeaderPanelMenu"
                class="ui-menu align-right hero-action-menu"
              >
                <slot v-if="hasHeaderPanelMenuSlot" name="app.header.panel.menu" />
                <slot v-else name="app.header.actions.menu" />
              </div>
            </template>

            <!-- Нижняя часть панели управления (опционально) -->
            <template v-if="hasHeaderPanelFooterSlot" #footer>
              <slot name="app.header.panel.footer" />
            </template>
          </UiHeroControlsAccordion>
        </aside>
      </section>

      <!-- Основной canvas страницы: верх, тело, низ -->
      <section class="blank-canvas" :aria-label="canvasAriaLabel">
        <!-- Верхняя зона canvas -->
        <section class="blank-canvas-top">
          <slot name="page.canvas.top" />
        </section>
        <!-- Центральная зона canvas (основной контент) -->
        <section class="blank-canvas-main">
          <slot name="page.canvas.main" />
        </section>
        <!-- Нижняя зона canvas -->
        <section class="blank-canvas-bottom">
          <slot name="page.canvas.bottom" />
        </section>
      </section>
    </section>

    <!-- Глобальные UI-слоты приложения -->
    <slot name="app.notifications" />
    <slot name="app.modals" />
    <slot name="app.command_palette" />

    <!-- Расширения для карточек сущностей -->
    <slot
      name="entity.card.actions"
      :context-object="entityContextObject"
      :required-capabilities="entityRequiredCapabilities"
    />
    <slot name="entity.card.badges" />
    <slot
      name="entity.card.inline"
      :context-object="entityContextObject"
      :required-capabilities="entityRequiredCapabilities"
    />
  </main>
</template>

<script setup lang="ts">
import { computed, ref, useSlots, watch } from "vue";
import { useRoute } from "vue-router";
import { FolderTree } from "lucide-vue-next";
import UiHeroGlassTabsShell from "@/components/layout/UiHeroGlassTabsShell.vue";
import UiHeroControlsAccordion from "@/components/layout/UiHeroControlsAccordion.vue";
import UiIconButton from "@/ui/actions/UiIconButton.vue";
import { useDashboardStore } from "@/features/stores/dashboardStore";

let sidebarBottomPanelCounter = 0;

const props = withDefaults(
  defineProps<{
    emblemSrc: string;
    sidebarHidden?: boolean;
    sidebarParticlesId?: string;
    sidebarBottomAccordionLabel?: string;
    sidebarBottomAccordionInitiallyOpen?: boolean;
    sidebarBottomVisible?: boolean | null;
    canvasAriaLabel?: string;
    headerPanelActive?: boolean;
    headerPanelDrawerId?: string;
    headerPanelStorageKey?: string;
    headerPanelInitiallyOpen?: boolean | null;
    layoutApiVersion?: "v1";
    entityContextObject?: Record<string, unknown> | null;
    entityRequiredCapabilities?: string[];
  }>(),
  {
    sidebarHidden: false,
    sidebarParticlesId: "",
    sidebarBottomAccordionLabel: "Sidebar details",
    sidebarBottomAccordionInitiallyOpen: true,
    sidebarBottomVisible: null,
    canvasAriaLabel: "Blank page",
    headerPanelActive: false,
    headerPanelDrawerId: "blank-hero-controls-drawer",
    headerPanelStorageKey: "",
    headerPanelInitiallyOpen: null,
    layoutApiVersion: "v1",
    entityContextObject: null,
    entityRequiredCapabilities: () => ["read.entity"],
  },
);

const emit = defineEmits<{
  "header-panel-open-change": [value: boolean];
}>();

const route = useRoute();
const dashboard = useDashboardStore();
const {
  isSidebarDetailed,
  sidebarView,
  sidebarViewToggleTitle,
  toggleSidebarView,
} = dashboard;
const slots = useSlots();
const hasHeaderLeft = computed(() => Boolean(slots["app.header.left"]));
const hasHeaderPanelMenuSlot = computed(() =>
  Boolean(slots["app.header.panel.menu"]),
);
const hasHeaderActionsMenuSlot = computed(() =>
  Boolean(slots["app.header.actions.menu"]),
);
const hasHeaderPanelMenu = computed(
  () => hasHeaderPanelMenuSlot.value || hasHeaderActionsMenuSlot.value,
);
const hasHeaderPanelFooterSlot = computed(() =>
  Boolean(slots["app.header.panel.footer"]),
);
const isSidebarBottomOpen = ref(
  Boolean(props.sidebarBottomAccordionInitiallyOpen),
);
const sidebarBottomPanelId = `blank-sidebar-bottom-panel-${++sidebarBottomPanelCounter}`;
const hasSidebarBottomSlot = computed(() =>
  Boolean(slots["app.sidebar.bottom"]),
);
const resolvedHeaderPanelStorageKey = computed(() => {
  const customKey = String(props.headerPanelStorageKey || "").trim();
  if (customKey) return customKey;
  const rawPath = String(route.path || "/").trim();
  const normalizedPath =
    rawPath.length > 1 && rawPath.endsWith("/")
      ? rawPath.slice(0, -1)
      : rawPath;
  return `oko:hero-controls-open:${normalizedPath || "/"}`;
});

const hasSidebarBottomContent = computed(() => {
  if (!hasSidebarBottomSlot.value) return false;
  if (typeof props.sidebarBottomVisible === "boolean") {
    return props.sidebarBottomVisible;
  }
  return true;
});

let hadSidebarBottomContent = false;
watch(
  () => hasSidebarBottomContent.value,
  (hasContent) => {
    if (!hasContent) {
      isSidebarBottomOpen.value = false;
      hadSidebarBottomContent = false;
      return;
    }
    if (!hadSidebarBottomContent) {
      isSidebarBottomOpen.value = Boolean(
        props.sidebarBottomAccordionInitiallyOpen,
      );
      hadSidebarBottomContent = true;
    }
  },
  { immediate: true },
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
</script>

<style scoped>
.blank-page {
  grid-template-columns: 420px minmax(0, 1fr);
}

.blank-page,
.blank-page :deep(*) {
  animation: none !important;
  transition: none !important;
}

.blank-page.sidebar-hidden {
  grid-template-columns: minmax(0, 1fr);
}

.blank-main {
  position: relative;
  isolation: isolate;
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 10px;
  overflow: visible;
}

.blank-main-header {
  position: relative;
  z-index: 50;
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

.blank-header-left,
.blank-header-tabs {
  display: contents;
}

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
  background: linear-gradient(
    146deg,
    rgba(15, 34, 51, 0.5),
    rgba(10, 24, 40, 0.36)
  );
  padding: 0 10px;
  transition:
    max-height 230ms ease,
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
  background: linear-gradient(
    146deg,
    rgba(20, 45, 68, 0.56),
    rgba(12, 30, 48, 0.45)
  );
  color: rgba(220, 237, 250, 0.95);
  padding: 9px 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 0.82rem;
  letter-spacing: 0.03em;
  cursor: pointer;
  transition:
    border-color 170ms ease,
    box-shadow 170ms ease,
    background 170ms ease;
}

.blank-sidebar-accordion__trigger:hover {
  border-color: rgba(157, 216, 250, 0.52);
  background: linear-gradient(
    146deg,
    rgba(30, 63, 93, 0.58),
    rgba(17, 41, 65, 0.52)
  );
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

.blank-canvas {
  position: relative;
  z-index: 1;
  border: 1px solid rgba(89, 144, 166, 0.18);
  border-radius: var(--ui-radius);
  background: transparent;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
  padding: clamp(14px, 2vw, 24px);
  overflow: hidden;
  display: grid;
  align-content: start;
  gap: 10px;
}

.blank-canvas-top,
.blank-canvas-main,
.blank-canvas-bottom {
  min-width: 0;
  min-height: 0;
}
</style>
