<template>
  <UiHeroPanel controls-class="hero-control-panel--menu service-hero-controls">
    <template #title>
      <nav
        ref="tabsRef"
        class="hero-page-tabs hero-page-tabs--js-smooth"
        :class="{
          'hero-page-tabs--intro': shouldPlayIntro,
          'has-logo-tile': showLogoTile,
        }"
        role="tablist"
        aria-label="Разделы blank страницы"
      >
        <div v-if="showLogoTile" class="hero-logo-square" aria-hidden="true">
          <img :src="EMBLEM_SRC" alt="" />
        </div>

        <button
          v-for="tab in demoTabs"
          :key="tab.id"
          :id="`blank-tab-${tab.id}`"
          class="hero-page-tab-btn"
          :data-page-id="tab.id"
          :class="{
            active: activeTabId === tab.id,
            'hero-page-tab-btn--intro-active':
              shouldPlayIntro && activeTabId === tab.id,
          }"
          type="button"
          role="tab"
          :title="tab.label"
          :aria-label="tab.label"
          :aria-selected="activeTabId === tab.id"
          :tabindex="activeTabId === tab.id ? 0 : -1"
          :aria-controls="`blank-panel-${tab.id}`"
          @click="activeTabId = tab.id"
        >
          <component :is="tab.icon" class="ui-icon hero-page-tab-icon" />
          <span class="hero-page-tab-label">{{ tab.label }}</span>
        </button>
      </nav>
    </template>

    <template #controls>
      <UiHeroControlsAccordion
        drawer-id="blank-hero-controls-drawer"
        :storage-key="heroControlsStorageKey"
        :initial-open="resolvedHeroControlsOpen"
        @open-change="handleHeroControlsOpenChange"
      >
        <template #drawer>
          <UiIconButton
            button-class="hero-icon-btn hero-accordion-action"
            :active="!isSidebarDetailed"
            :title="sidebarViewToggleTitle"
            :aria-label="sidebarViewToggleTitle"
            @click="handleSidebarToggle"
          >
            <FolderTree class="ui-icon hero-action-icon" />
          </UiIconButton>
        </template>

        <template #actions>
          <UiDropdownMenu
            class="hero-action-menu"
            aria-label="Системное меню"
            :items="systemActions"
            :show-caret="false"
            trigger-class="hero-icon-btn hero-accordion-action hero-system-menu-trigger"
            item-class="hero-system-menu-item"
            @action="handleSystemAction"
          >
            <template #trigger>
              <ChevronDown class="ui-icon hero-action-icon" />
            </template>
          </UiDropdownMenu>
        </template>
      </UiHeroControlsAccordion>
    </template>
  </UiHeroPanel>
</template>

<script setup lang="ts">
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
  type Component,
} from "vue";
import { useRoute } from "vue-router";
import { ChevronDown, FolderTree, Lock } from "lucide-vue-next";
import UiIconButton from "@/ui/actions/UiIconButton.vue";
import UiHeroControlsAccordion from "@/components/layout/UiHeroControlsAccordion.vue";
import UiHeroPanel from "@/components/layout/UiHeroPanel.vue";
import UiDropdownMenu from "@/primitives/overlays/UiDropdownMenu.vue";
import { openPleiadOverlay } from "@/app/navigation/nav";
import { getRuntimeProfile } from "@/features/services/desktopRuntime";
import { useDashboardStore } from "@/features/stores/dashboardStore";

type BlankTabId = "overview" | "operations";
type BlankTabDefinition = {
  id: BlankTabId;
  label: string;
  icon: Component;
};

const props = withDefaults(
  defineProps<{
    modelValue?: BlankTabId;
    heroControlsOpen?: boolean;
  }>(),
  {
    modelValue: "overview",
    heroControlsOpen: true,
  },
);

const emit = defineEmits<{
  "update:modelValue": [tabId: BlankTabId];
  "update:heroControlsOpen": [value: boolean];
}>();

let hasPlayedBlankTabsIntro = false;
const route = useRoute();
const dashboard = useDashboardStore();
const {
  EMBLEM_SRC,
  isSidebarHidden,
  isSidebarDetailed,
  openSettingsPanel,
  sidebarView,
  sidebarViewToggleTitle,
  toggleSidebarView,
} = dashboard;
const demoTabs: BlankTabDefinition[] = [
  { id: "overview", label: "Обзор пространства", icon: FolderTree },
  { id: "operations", label: "Оперативный контур", icon: Lock },
];
const tabsRef = ref<HTMLElement | null>(null);
const shouldPlayIntro = ref(!hasPlayedBlankTabsIntro);

type SystemActionId = "kiosk" | "profile" | "lock" | "exit";

const systemActions: Array<{
  id: SystemActionId;
  label: string;
  icon: string;
  danger?: boolean;
}> = [
  { id: "kiosk", label: "Режим киоска", icon: "⌗" },
  { id: "profile", label: "Профиль", icon: "◉" },
  { id: "lock", label: "Блокировка", icon: "⛨" },
  { id: "exit", label: "Выход", icon: "⏻", danger: true },
];

const heroControlsStorageKey = computed(() => {
  const rawPath = String(route.path || "/").trim();
  const normalizedPath = rawPath.length > 1 && rawPath.endsWith("/")
    ? rawPath.slice(0, -1)
    : rawPath;
  return `oko:hero-controls-open:${normalizedPath || "/"}`;
});
const showLogoTile = computed(() => isSidebarHidden.value);
const resolvedHeroControlsOpen = computed(() => Boolean(props.heroControlsOpen));
const tabIdsSignature = computed(() => demoTabs.map((tab) => tab.id).join("|"));
const activeTabId = computed<BlankTabId>({
  get: () => {
    const value = String(props.modelValue || "overview") as BlankTabId;
    return demoTabs.some((tab) => tab.id === value) ? value : "overview";
  },
  set: (value) => {
    emit("update:modelValue", value);
  },
});

function handleSidebarToggle(): void {
  const before = sidebarView.value;
  toggleSidebarView();
  if (sidebarView.value !== before) return;
  sidebarView.value = before === "hidden" ? "detailed" : "hidden";
}

function handleHeroControlsOpenChange(value: boolean): void {
  emit("update:heroControlsOpen", value);
}

interface TabMetrics {
  collapsedWidth: number;
  iconWidth: number;
  slideDuration: number;
  expandedPadding: number;
  expandedGap: number;
  collapsedPadding: number;
  activeWidth: number;
}

interface TabDescriptor {
  button: HTMLElement;
  label: HTMLElement | null;
  from: number;
  to: number;
}

let introTimeoutId: number | null = null;
let tabsAnimationFrameId: number | null = null;
let tabsResizeFrameId: number | null = null;
let tabsResizeObserver: ResizeObserver | null = null;
let fallbackResizeListenerAttached = false;

function parseCssNumber(rawValue: unknown, fallback: number): number {
  const parsed = Number.parseFloat(String(rawValue || ""));
  return Number.isFinite(parsed) ? parsed : fallback;
}

function getTabButtons(): HTMLElement[] {
  if (!tabsRef.value) return [];
  return Array.from(
    tabsRef.value.querySelectorAll<HTMLElement>(":scope > .hero-page-tab-btn"),
  );
}

function stopTabsAnimation(): void {
  if (!tabsAnimationFrameId) return;
  globalThis.cancelAnimationFrame(tabsAnimationFrameId);
  tabsAnimationFrameId = null;
}

function stopResizeSchedule(): void {
  if (!tabsResizeFrameId) return;
  globalThis.cancelAnimationFrame(tabsResizeFrameId);
  tabsResizeFrameId = null;
}

function resolveTabMetrics(buttons: HTMLElement[]): TabMetrics | null {
  const host = tabsRef.value;
  if (!host || !buttons.length) return null;

  const styles = globalThis.getComputedStyle(host);
  const collapsedWidth = parseCssNumber(
    styles.getPropertyValue("--hero-page-tab-size"),
    52,
  );
  const iconWidth = parseCssNumber(
    styles.getPropertyValue("--hero-page-tab-icon-size"),
    17,
  );
  const slideDuration = parseCssNumber(
    styles.getPropertyValue("--hero-tabs-slide-duration"),
    940,
  );
  const expandedPadding = 32;
  const expandedGap = 10;
  const collapsedPadding = Math.max(0, (collapsedWidth - iconWidth) / 2);

  const logoTile = host.querySelector<HTMLElement>(":scope > .hero-logo-square");
  const logoWidth = logoTile ? logoTile.getBoundingClientRect().width : 0;
  const overlapCompensation = Math.max(0, buttons.length - 1);
  const availableWidth = Math.max(
    collapsedWidth * buttons.length,
    host.clientWidth - logoWidth + overlapCompensation,
  );
  const activeWidth = Math.max(
    collapsedWidth,
    availableWidth - collapsedWidth * (buttons.length - 1),
  );

  return {
    collapsedWidth,
    iconWidth,
    slideDuration,
    expandedPadding,
    expandedGap,
    collapsedPadding,
    activeWidth,
  };
}

function readButtonWidth(
  button: HTMLElement | null | undefined,
  fallbackWidth: number,
): number {
  const cachedWidth = parseCssNumber(button?.dataset?.tabWidth, 0);
  if (cachedWidth > 0) return cachedWidth;

  const measuredWidth = button?.getBoundingClientRect?.().width || 0;
  if (measuredWidth > 0) return measuredWidth;

  return fallbackWidth;
}

function applyTabFrame(
  descriptors: TabDescriptor[],
  metrics: TabMetrics,
  frameProgress: number,
): void {
  const transitionRange = Math.max(
    1,
    metrics.activeWidth - metrics.collapsedWidth,
  );
  const safeProgress = Math.max(0, Math.min(1, frameProgress));

  for (const descriptor of descriptors) {
    const width =
      descriptor.from + (descriptor.to - descriptor.from) * safeProgress;
    const tabProgress = Math.max(
      0,
      Math.min(1, (width - metrics.collapsedWidth) / transitionRange),
    );
    const paddingInline =
      metrics.collapsedPadding +
      (metrics.expandedPadding - metrics.collapsedPadding) * tabProgress;
    const gap = metrics.expandedGap * tabProgress;
    const labelMaxWidth = Math.max(
      0,
      width - paddingInline * 2 - metrics.iconWidth - gap - 6,
    );

    descriptor.button.style.flexGrow = "0";
    descriptor.button.style.flexShrink = "0";
    descriptor.button.style.flexBasis = "auto";
    descriptor.button.style.width = `${width.toFixed(3)}px`;
    descriptor.button.style.minWidth = `${width.toFixed(3)}px`;
    descriptor.button.style.paddingInline = `${paddingInline.toFixed(3)}px`;
    descriptor.button.style.gap = `${gap.toFixed(3)}px`;
    descriptor.button.style.setProperty(
      "--hero-tab-progress",
      tabProgress.toFixed(4),
    );
    descriptor.button.dataset.tabWidth = width.toFixed(3);

    if (!descriptor.label) continue;
    descriptor.label.style.maxInlineSize = `${labelMaxWidth.toFixed(3)}px`;
    descriptor.label.style.opacity = `${(0.98 * tabProgress).toFixed(4)}`;
    descriptor.label.style.marginLeft = `${(4 * tabProgress).toFixed(3)}px`;
    descriptor.label.style.transform = `translateX(${(
      -10 * (1 - tabProgress)
    ).toFixed(3)}px)`;
  }
}

function easeInOutQuart(progress: number): number {
  if (progress < 0.5) {
    return 8 * progress ** 4;
  }
  return 1 - ((-2 * progress + 2) ** 4) / 2;
}

function animateTabsLayout({ instant = false }: { instant?: boolean } = {}): void {
  const buttons = getTabButtons();
  if (!buttons.length) return;

  const metrics = resolveTabMetrics(buttons);
  if (!metrics) return;

  const activeId = String(activeTabId.value || demoTabs[0]?.id || "");
  let activeIndex = buttons.findIndex(
    (button) => String(button.dataset.pageId || "") === activeId,
  );
  if (activeIndex < 0) {
    activeIndex = 0;
  }

  const descriptors: TabDescriptor[] = buttons.map((button, index) => {
    const targetWidth =
      index === activeIndex ? metrics.activeWidth : metrics.collapsedWidth;
    return {
      button,
      label: button.querySelector<HTMLElement>(".hero-page-tab-label"),
      from: readButtonWidth(button, targetWidth),
      to: targetWidth,
    };
  });

  const noDelta = descriptors.every(
    (descriptor) => Math.abs(descriptor.to - descriptor.from) < 0.35,
  );
  if (instant || noDelta) {
    stopTabsAnimation();
    applyTabFrame(descriptors, metrics, 1);
    return;
  }

  stopTabsAnimation();
  const durationMs = Math.max(560, Math.min(1800, metrics.slideDuration * 1.15));
  const startedAt = globalThis.performance.now();

  const step = (timestamp: number) => {
    const elapsed = timestamp - startedAt;
    const progress = Math.max(0, Math.min(1, elapsed / durationMs));
    const eased = easeInOutQuart(progress);
    applyTabFrame(descriptors, metrics, eased);

    if (progress < 1) {
      tabsAnimationFrameId = globalThis.requestAnimationFrame(step);
      return;
    }
    tabsAnimationFrameId = null;
  };

  tabsAnimationFrameId = globalThis.requestAnimationFrame(step);
}

function scheduleInstantTabsLayout(): void {
  stopResizeSchedule();
  tabsResizeFrameId = globalThis.requestAnimationFrame(() => {
    tabsResizeFrameId = null;
    animateTabsLayout({ instant: true });
  });
}

async function toggleKioskMode(): Promise<void> {
  if (typeof document === "undefined") return;
  try {
    if (document.fullscreenElement) {
      await document.exitFullscreen();
      return;
    }
    await document.documentElement.requestFullscreen();
  } catch {
    // Keep UI responsive even if fullscreen API is unavailable.
  }
}

async function exitApp(): Promise<void> {
  try {
    if (getRuntimeProfile().desktop) {
      const { getCurrentWindow } = await import("@tauri-apps/api/window");
      await getCurrentWindow().close();
      return;
    }
  } catch {
    // Fall through to browser close attempt.
  }

  if (typeof window !== "undefined") {
    window.close();
  }
}

function handleSystemAction(actionId: string): void {
  const id = actionId as SystemActionId;

  if (id === "kiosk") {
    void toggleKioskMode();
    return;
  }

  if (id === "profile") {
    openSettingsPanel();
    return;
  }

  if (id === "lock") {
    void openPleiadOverlay("route");
    return;
  }

  if (id === "exit") {
    void exitApp();
  }
}

onMounted(() => {
  nextTick(() => {
    animateTabsLayout({ instant: true });
  });

  if ("ResizeObserver" in globalThis) {
    tabsResizeObserver = new globalThis.ResizeObserver(() => {
      scheduleInstantTabsLayout();
    });
    if (tabsRef.value) {
      tabsResizeObserver.observe(tabsRef.value);
    }
  } else {
    globalThis.addEventListener("resize", scheduleInstantTabsLayout);
    fallbackResizeListenerAttached = true;
  }

  if (!shouldPlayIntro.value) return;
  introTimeoutId = globalThis.setTimeout(() => {
    shouldPlayIntro.value = false;
    hasPlayedBlankTabsIntro = true;
  }, 700);
});

watch(
  [activeTabId, tabIdsSignature, showLogoTile],
  async () => {
    await nextTick();
    animateTabsLayout({ instant: false });
  },
);

onBeforeUnmount(() => {
  stopTabsAnimation();
  stopResizeSchedule();

  if (tabsResizeObserver) {
    tabsResizeObserver.disconnect();
    tabsResizeObserver = null;
  }
  if (fallbackResizeListenerAttached) {
    globalThis.removeEventListener("resize", scheduleInstantTabsLayout);
    fallbackResizeListenerAttached = false;
  }

  if (introTimeoutId) {
    globalThis.clearTimeout(introTimeoutId);
    introTimeoutId = null;
  }
  if (shouldPlayIntro.value) {
    hasPlayedBlankTabsIntro = true;
  }
});
</script>
