<template>
  <nav
    ref="tabsRef"
    class="hero-page-tabs"
    :class="{
      'hero-page-tabs--js-smooth': !homeOnly,
      'hero-page-tabs--intro': !homeOnly && shouldPlayIntro,
      'has-logo-tile': showLogoTile,
    }"
    :aria-label="homeOnly ? 'Навигация' : 'Разделы'"
    :role="homeOnly ? undefined : 'tablist'"
  >
    <div v-if="showLogoTile" class="hero-logo-square" aria-hidden="true">
      <img :src="EMBLEM_SRC" alt="" />
    </div>

    <template v-if="homeOnly">
      <button
        v-if="homePage"
        class="hero-page-tab-btn hero-page-tab-btn--home"
        :class="{ active: activePage?.id === homePage.id }"
        type="button"
        :title="homeButtonTitle"
        :aria-label="homeButtonTitle"
        @click="openHomePage"
      >
        <House class="ui-icon hero-page-tab-icon" />
      </button>
    </template>

    <template v-else>
      <button
        v-for="page in pages"
        :key="page.id"
        class="hero-page-tab-btn"
        :data-page-id="page.id"
        :class="{
          active: activePage?.id === page.id,
          'hero-page-tab-btn--intro-active':
            shouldPlayIntro && activePage?.id === page.id,
        }"
        type="button"
        role="tab"
        :title="page.title"
        :aria-label="page.title"
        :aria-selected="activePage?.id === page.id"
        @click="activePageId = page.id"
      >
        <component
          :is="resolvePageIcon(page)"
          class="ui-icon hero-page-tab-icon"
        />
        <span class="hero-page-tab-label">{{ page.title }}</span>
      </button>
    </template>
  </nav>
</template>

<script setup>
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from "vue";
import { House } from "lucide-vue-next";
import { useDashboardStore } from "../../stores/dashboardStore.js";

const props = defineProps({
  variant: {
    type: String,
    default: "full",
  },
});

let hasPlayedHeroTabsIntro = false;

const dashboard = useDashboardStore();
const {
  EMBLEM_SRC,
  isSidebarHidden,
  pages,
  activePage,
  activePageId,
  resolvePageIcon,
} = dashboard;
const shouldPlayIntro = ref(!hasPlayedHeroTabsIntro);
const showLogoTile = computed(() => isSidebarHidden.value);
const homeOnly = computed(() => props.variant === "home");
const homePage = computed(() => pages.value?.[0] || null);
const pageIdsSignature = computed(() =>
  (pages.value || []).map((page) => String(page?.id || "")).join("|"),
);
const homeButtonTitle = computed(
  () =>
    `Домой${homePage.value?.title ? ` (${String(homePage.value.title)})` : ""}`,
);
const tabsRef = ref(null);

let introTimeoutId = 0;
let tabsAnimationFrameId = 0;
let tabsResizeFrameId = 0;
let tabsResizeObserver = null;
let fallbackResizeListenerAttached = false;

function openHomePage() {
  if (!homePage.value?.id) return;
  activePageId.value = homePage.value.id;
}

function parseCssNumber(rawValue, fallback) {
  const parsed = Number.parseFloat(String(rawValue || ""));
  return Number.isFinite(parsed) ? parsed : fallback;
}

function getTabButtons() {
  if (!tabsRef.value) return [];
  return Array.from(
    tabsRef.value.querySelectorAll(":scope > .hero-page-tab-btn"),
  );
}

function stopTabsAnimation() {
  if (!tabsAnimationFrameId) return;
  globalThis.cancelAnimationFrame(tabsAnimationFrameId);
  tabsAnimationFrameId = 0;
}

function stopResizeSchedule() {
  if (!tabsResizeFrameId) return;
  globalThis.cancelAnimationFrame(tabsResizeFrameId);
  tabsResizeFrameId = 0;
}

function resolveTabMetrics(buttons) {
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

  const logoTile = host.querySelector(":scope > .hero-logo-square");
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

function readButtonWidth(button, fallbackWidth) {
  const cachedWidth = parseCssNumber(button?.dataset?.tabWidth, 0);
  if (cachedWidth > 0) return cachedWidth;

  const measuredWidth = button?.getBoundingClientRect?.().width || 0;
  if (measuredWidth > 0) return measuredWidth;

  return fallbackWidth;
}

function applyTabFrame(descriptors, metrics, frameProgress) {
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

function easeInOutQuart(progress) {
  if (progress < 0.5) {
    return 8 * progress ** 4;
  }
  return 1 - ((-2 * progress + 2) ** 4) / 2;
}

function animateTabsLayout({ instant = false } = {}) {
  if (homeOnly.value) return;

  const buttons = getTabButtons();
  if (!buttons.length) return;

  const metrics = resolveTabMetrics(buttons);
  if (!metrics) return;

  const activeId = String(
    activePage.value?.id || pages.value?.[0]?.id || buttons[0]?.dataset?.pageId,
  );
  let activeIndex = buttons.findIndex(
    (button) => String(button.dataset.pageId || "") === activeId,
  );
  if (activeIndex < 0) {
    activeIndex = 0;
  }

  const descriptors = buttons.map((button, index) => {
    const targetWidth =
      index === activeIndex ? metrics.activeWidth : metrics.collapsedWidth;
    return {
      button,
      label: button.querySelector(".hero-page-tab-label"),
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

  const step = (timestamp) => {
    const elapsed = timestamp - startedAt;
    const progress = Math.max(0, Math.min(1, elapsed / durationMs));
    const eased = easeInOutQuart(progress);
    applyTabFrame(descriptors, metrics, eased);

    if (progress < 1) {
      tabsAnimationFrameId = globalThis.requestAnimationFrame(step);
      return;
    }
    tabsAnimationFrameId = 0;
  };

  tabsAnimationFrameId = globalThis.requestAnimationFrame(step);
}

function scheduleInstantTabsLayout() {
  if (homeOnly.value) return;
  stopResizeSchedule();
  tabsResizeFrameId = globalThis.requestAnimationFrame(() => {
    tabsResizeFrameId = 0;
    animateTabsLayout({ instant: true });
  });
}

onMounted(() => {
  if (!homeOnly.value) {
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
  }

  if (homeOnly.value || !shouldPlayIntro.value) return;

  introTimeoutId = globalThis.setTimeout(() => {
    shouldPlayIntro.value = false;
    hasPlayedHeroTabsIntro = true;
  }, 700);
});

watch(
  [() => activePage.value?.id || "", pageIdsSignature, showLogoTile, homeOnly],
  async ([, , , isHome]) => {
    if (isHome) return;
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

  if (homeOnly.value) return;
  if (introTimeoutId) {
    globalThis.clearTimeout(introTimeoutId);
    introTimeoutId = 0;
  }
  if (shouldPlayIntro.value) {
    hasPlayedHeroTabsIntro = true;
  }
});
</script>
