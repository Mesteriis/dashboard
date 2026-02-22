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

<script setup>
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  toRef,
  watch,
} from "vue";
import ServiceItemCard from "./ServiceItemCard.vue";
import { useDashboardStore } from "../../stores/dashboardStore.js";

const VIRTUALIZATION_THRESHOLD = 120;
const BATCH_SIZE = 72;

const props = defineProps({
  items: {
    type: Array,
    required: true,
  },
  groupKey: {
    type: String,
    required: true,
  },
  subgroupId: {
    type: String,
    required: true,
  },
});

const itemsRef = toRef(props, "items");
const dashboard = useDashboardStore();
const { isIconCardView, isTileCardView } = dashboard;

const sentinelRef = ref(null);
const visibleCount = ref(BATCH_SIZE);
let observer = null;

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

function loadMore() {
  visibleCount.value = Math.min(
    itemsRef.value.length,
    visibleCount.value + BATCH_SIZE,
  );
}

function resetVisibleItems() {
  visibleCount.value = BATCH_SIZE;
}

function syncObserverTarget() {
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
