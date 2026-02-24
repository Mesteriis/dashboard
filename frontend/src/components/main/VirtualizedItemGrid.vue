<template>
  <div class="virtual-item-grid">
    <TransitionGroup
      name="item-grid-transition"
      tag="div"
      class="item-grid"
      :class="{
        'icon-card-grid': isIconCardView,
        'tile-card-grid': isTileCardView,
      }"
    >
      <ServiceItemCard
        v-for="item in renderedItems"
        :key="item.id"
        :group-key="item.__originGroupKey || groupKey"
        :subgroup-id="item.__originSubgroupId || subgroupId"
        :item="item"
      />
    </TransitionGroup>

    <div
      v-if="hasMore"
      ref="sentinelRef"
      class="item-grid-sentinel"
      aria-hidden="true"
    ></div>
  </div>
</template>

<script setup lang="ts">
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  toRef,
  watch,
} from "vue";
import ServiceItemCard from "@/components/main/ServiceItemCard.vue";
import { useDashboardStore } from "@/stores/dashboardStore";

const VIRTUALIZATION_THRESHOLD = 120;
const BATCH_SIZE = 72;

interface VirtualizedItem {
  id: string;
  __originGroupKey?: string;
  __originSubgroupId?: string;
  [key: string]: unknown;
}

const props = defineProps<{
  items: VirtualizedItem[];
  groupKey: string;
  subgroupId: string;
}>();

const itemsRef = toRef(props, "items");
const dashboard = useDashboardStore();
const { isIconCardView, isTileCardView } = dashboard;

const sentinelRef = ref<HTMLElement | null>(null);
const visibleCount = ref(BATCH_SIZE);
let observer: IntersectionObserver | null = null;

const shouldVirtualize = computed(
  () => itemsRef.value.length > VIRTUALIZATION_THRESHOLD,
);
const hasMore = computed(
  () => shouldVirtualize.value && visibleCount.value < itemsRef.value.length,
);
const renderedItems = computed(() => {
  if (!shouldVirtualize.value) return itemsRef.value;
  return itemsRef.value.slice(0, visibleCount.value);
});

function loadMore(): void {
  visibleCount.value = Math.min(
    itemsRef.value.length,
    visibleCount.value + BATCH_SIZE,
  );
}

function resetVisibleItems(): void {
  visibleCount.value = BATCH_SIZE;
}

function syncObserverTarget(): void {
  if (!observer) return;
  observer.disconnect();
  if (!hasMore.value || !sentinelRef.value) return;
  observer.observe(sentinelRef.value);
}

watch(
  () => itemsRef.value,
  async () => {
    resetVisibleItems();
    await nextTick();
    syncObserverTarget();
  },
  { deep: true },
);

watch(
  () => hasMore.value,
  async () => {
    await nextTick();
    syncObserverTarget();
  },
);

onMounted(async () => {
  observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          loadMore();
          break;
        }
      }
    },
    {
      root: null,
      rootMargin: "260px 0px",
      threshold: 0,
    },
  );
  await nextTick();
  syncObserverTarget();
});

onBeforeUnmount(() => {
  observer?.disconnect();
  observer = null;
});
</script>
