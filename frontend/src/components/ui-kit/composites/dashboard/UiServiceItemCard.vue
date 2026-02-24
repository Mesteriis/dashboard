<template>
  <article
    class="item-card"
    :class="itemCardClasses"
    :title="isCompactServiceCardView ? serviceItem.title : undefined"
    :role="editMode ? undefined : 'button'"
    :tabindex="editMode ? -1 : 0"
    @click="handleCardClick"
    @keydown.enter.prevent="handleCardClick"
    @keydown.space.prevent="handleCardClick"
  >
    <template v-if="isIconCardView">
      <UiIconButton
        v-if="editMode"
        class="item-inline-edit item-inline-edit-compact"
        title="Редактировать элемент"
        aria-label="Редактировать элемент"
        @click.stop="openEditItem"
      >
        <Pencil class="ui-icon item-action-icon" />
      </UiIconButton>
      <div class="item-compact-body">
        <img
          v-if="itemFaviconSrc(item)"
          :src="itemFaviconSrc(item)"
          class="service-favicon compact-item-favicon"
          alt=""
          loading="lazy"
          referrerpolicy="no-referrer"
          @error="markItemFaviconFailed(item)"
        />
        <component
          v-else
          :is="resolveItemIcon(item)"
          class="ui-icon item-icon compact-item-icon"
        />
        <span
          v-if="showHealthIndicators"
          class="health-dot compact-health-dot"
          :class="healthVisualClass"
        ></span>
      </div>
    </template>

    <template v-else-if="isTileCardView">
      <UiIconButton
        v-if="editMode"
        class="item-inline-edit item-inline-edit-tile"
        title="Редактировать элемент"
        aria-label="Редактировать элемент"
        @click.stop="openEditItem"
      >
        <Pencil class="ui-icon item-action-icon" />
      </UiIconButton>
      <div class="item-tile-head">
        <img
          v-if="itemFaviconSrc(item)"
          :src="itemFaviconSrc(item)"
          class="service-favicon tile-item-favicon"
          alt=""
          loading="lazy"
          referrerpolicy="no-referrer"
          @error="markItemFaviconFailed(item)"
        />
        <component
          v-else
          :is="resolveItemIcon(item)"
          class="ui-icon item-icon tile-item-icon"
        />
        <span
          v-if="showHealthIndicators"
          class="health-dot tile-health-dot"
          :class="healthVisualClass"
        ></span>
      </div>
      <p class="item-tile-title">{{ serviceItem.title }}</p>
    </template>

    <template v-else>
      <div class="item-head">
        <div class="item-title-row">
          <img
            v-if="itemFaviconSrc(item)"
            :src="itemFaviconSrc(item)"
            class="service-favicon item-favicon"
            alt=""
            loading="lazy"
            referrerpolicy="no-referrer"
            @error="markItemFaviconFailed(item)"
          />
          <component
            v-else
            :is="resolveItemIcon(item)"
            class="ui-icon item-icon"
          />
          <h4>{{ serviceItem.title }}</h4>
        </div>
        <div class="item-kind-pills">
          <span class="item-type">{{ serviceItem.type }}</span>
        </div>
      </div>

      <p class="item-url">{{ serviceItem.url }}</p>
      <p
        v-if="showHealthIndicators && serviceItem.check_url && serviceItem.check_url !== serviceItem.url"
        class="item-check-url"
      >
        check: {{ serviceItem.check_url }}
      </p>
      <div v-if="showHealthIndicators" class="item-health">
        <span class="health-dot" :class="healthVisualClass"></span>
        <span
          class="health-text"
          :class="{ 'is-updating': healthFlashActive }"
          >{{ healthLabelText }}</span
        >
      </div>

      <div v-if="siteLabel || serviceItem.tags.length" class="item-tags">
        <span v-if="siteLabel" class="tag-pill site-pill"
          >site:{{ siteLabel }}</span
        >
        <span v-for="tag in serviceItem.tags" :key="tag" class="tag-pill">{{
          tag
        }}</span>
      </div>

      <ServiceItemPluginExtensions
        v-if="serviceItem.plugin_blocks.length"
        :item-id="serviceItem.id"
        :blocks="serviceItem.plugin_blocks"
        @open-link="openPluginLink"
        @copy-link="copyPluginText"
      />
      <slot name="plugin-content" :item="serviceItem"></slot>

      <div class="item-actions">
        <UiIconButton
          v-if="editMode"
          title="Редактировать элемент"
          aria-label="Редактировать элемент"
          @click.stop="openEditItem"
        >
          <Pencil class="ui-icon item-action-icon" />
        </UiIconButton>
        <UiIconButton
          :title="serviceItem.type === 'iframe' ? 'Открыть iframe' : 'Открыть'"
          :aria-label="
            serviceItem.type === 'iframe' ? 'Открыть iframe' : 'Открыть'
          "
          @click.stop="openItem(item)"
        >
          <component
            :is="serviceItem.type === 'iframe' ? Globe : ExternalLink"
            class="ui-icon item-action-icon"
          />
        </UiIconButton>
        <UiIconButton
          title="Копировать URL"
          aria-label="Копировать URL"
          @click.stop="copyUrl(serviceItem.url)"
        >
          <Copy class="ui-icon item-action-icon" />
        </UiIconButton>
      </div>
    </template>
  </article>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, toRef, watch } from "vue";
import { Copy, ExternalLink, Globe, Pencil } from "lucide-vue-next";
import ServiceItemPluginExtensions from "@/components/ui-kit/composites/dashboard/UiServiceItemPluginExtensions.vue";
import UiIconButton from "@/components/ui-kit/primitives/UiIconButton.vue";
import {
  normalizeServiceCardCore,
  type ServiceCardCoreV1,
  type ServiceCardOpenV1,
} from "@/contracts/serviceCard";
import { useDashboardStore } from "@/stores/dashboardStore";

interface ServiceItem {
  id: string;
  title?: string;
  type?: string;
  url?: string;
  tags?: string[];
  [key: string]: unknown;
}

const props = defineProps<{
  groupKey: string;
  subgroupId: string;
  item: ServiceItem;
}>();

const groupKey = toRef(props, "groupKey");
const subgroupId = toRef(props, "subgroupId");
const item = toRef(props, "item");
const serviceItem = computed<ServiceCardCoreV1>(() =>
  normalizeServiceCardCore(item.value),
);

const dashboard = useDashboardStore();

const {
  isIconCardView,
  isTileCardView,
  isCompactServiceCardView,
  isItemSelected,
  editMode,
  editItem,
  onItemCardClick,
  itemFaviconSrc,
  markItemFaviconFailed,
  resolveItemIcon,
  healthClass,
  healthLabel,
  itemSite,
  openItem,
  copyUrl,
} = dashboard;

function parseBoolean(value: unknown): boolean | null {
  if (typeof value === "boolean") return value;
  if (typeof value === "string") {
    const normalized = value.trim().toLowerCase();
    if (["1", "true", "yes", "on"].includes(normalized)) return true;
    if (["0", "false", "no", "off"].includes(normalized)) return false;
  }
  return null;
}

const healthcheckEnabled = computed<boolean>(() => {
  const rawItem = item.value as Record<string, unknown>;
  const explicit = parseBoolean(rawItem.monitor_health);
  if (explicit != null) {
    return explicit;
  }
  return Boolean(rawItem.healthcheck || rawItem.check_url);
});

type HealthVisualClass = "ok" | "degraded" | "down" | "unknown";

const healthVisualClass = computed<HealthVisualClass>(() =>
  healthClass(serviceItem.value.id),
);
const effectiveHealthVisualClass = computed<HealthVisualClass>(() =>
  healthcheckEnabled.value ? healthVisualClass.value : "unknown",
);
const showHealthIndicators = computed<boolean>(() => healthcheckEnabled.value);
const healthLabelText = computed<string>(() =>
  String(healthLabel(serviceItem.value.id)),
);
const siteLabel = computed<string>(() =>
  String(itemSite(serviceItem.value, groupKey.value) || ""),
);
const healthFlashActive = ref(false);
const dataSweepActive = ref(false);
let healthFlashTimer: number | null = null;
let dataSweepTimer: number | null = null;
const animatedHealthTransitions = new Set<string>([
  "ok>degraded",
  "degraded>ok",
  "degraded>down",
  "down>degraded",
]);

const itemCardClasses = computed(() => ({
  selected:
    !isCompactServiceCardView.value && isItemSelected(serviceItem.value.id),
  compact: isCompactServiceCardView.value,
  tile: isTileCardView.value,
  editing: editMode.value,
  [`status-${effectiveHealthVisualClass.value}`]: showHealthIndicators.value,
  "data-updated": dataSweepActive.value,
}));

function handleCardClick(): void {
  if (editMode.value) return;
  onItemCardClick(groupKey.value, subgroupId.value, item.value);
}

function openEditItem(): void {
  const rawItem = item.value as Record<string, unknown>;
  const resolvedGroupKey = String(rawItem.__originGroupKey || groupKey.value || "");
  const resolvedSubgroupId = String(rawItem.__originSubgroupId || subgroupId.value || "");
  const resolvedGroupId = resolvedGroupKey.startsWith("group:")
    ? resolvedGroupKey.slice(6)
    : resolvedGroupKey;
  if (!resolvedGroupId || !resolvedSubgroupId) {
    return;
  }
  void editItem(resolvedGroupId, resolvedSubgroupId, serviceItem.value.id);
}

function openPluginLink(url: string, openMode: ServiceCardOpenV1): void {
  openItem({
    type: "link",
    url,
    open: openMode,
  });
}

function copyPluginText(value: string): void {
  void copyUrl(value);
}

function triggerHealthFlash(): void {
  if (healthFlashTimer) {
    window.clearTimeout(healthFlashTimer);
  }
  healthFlashActive.value = false;
  window.requestAnimationFrame(() => {
    healthFlashActive.value = true;
    healthFlashTimer = window.setTimeout(() => {
      healthFlashActive.value = false;
      healthFlashTimer = null;
    }, 900);
  });
}

function triggerDataSweep(): void {
  if (dataSweepTimer) {
    window.clearTimeout(dataSweepTimer);
  }
  dataSweepActive.value = false;
  window.requestAnimationFrame(() => {
    dataSweepActive.value = true;
    dataSweepTimer = window.setTimeout(() => {
      dataSweepActive.value = false;
      dataSweepTimer = null;
    }, 1250);
  });
}

function shouldAnimateHealthTransition(
  prevClass: HealthVisualClass | undefined,
  nextClass: HealthVisualClass,
): boolean {
  if (!prevClass || prevClass === nextClass) {
    return false;
  }
  return animatedHealthTransitions.has(`${prevClass}>${nextClass}`);
}

watch(healthVisualClass, (nextClass, prevClass) => {
  if (!shouldAnimateHealthTransition(prevClass, nextClass)) {
    return;
  }
  triggerDataSweep();
  triggerHealthFlash();
});

onBeforeUnmount(() => {
  if (healthFlashTimer) {
    window.clearTimeout(healthFlashTimer);
    healthFlashTimer = null;
  }
  if (dataSweepTimer) {
    window.clearTimeout(dataSweepTimer);
    dataSweepTimer = null;
  }
});
</script>
