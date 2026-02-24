<template>
  <section ref="blocksRootRef" class="page-stack">
    <section
      v-for="(block, index) in activePageGroupBlocks"
      :key="`${activePage.id}:${index}:groups`"
      class="block-wrap"
    >
      <section v-auto-animate="groupsAutoAnimateOptions" class="groups-grid">
        <ServiceGroupCard
          v-for="group in filteredBlockGroups(block.group_ids)"
          :key="group.key"
          :group="group"
        />

        <article
          v-if="!filteredBlockGroups(block.group_ids).length"
          class="panel group-panel group-empty"
        >
          <h2>Нет данных для выбранного узла</h2>
          <p class="subtitle">Выберите другую ветку в боковом дереве.</p>
        </article>
      </section>
    </section>

    <article
      v-if="!activePageGroupBlocks.length"
      class="panel group-panel group-empty"
    >
      <h2>Для этой страницы нет групп</h2>
      <p class="subtitle">Откройте нужный индикатор в аккордеоне слева.</p>
    </article>
  </section>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { vAutoAnimate } from "@formkit/auto-animate/vue";
import ServiceGroupCard from "@/components/main/ServiceGroupCard.vue";
import { useDashboardStore } from "@/stores/dashboardStore";

const dashboard = useDashboardStore();
const { activePage, activePageGroupBlocks, filteredBlockGroups } = dashboard;
const blocksRootRef = ref<HTMLElement | null>(null);
let visibilityObserver: IntersectionObserver | null = null;
const groupsAutoAnimateOptions = {
  duration: 180,
  easing: "cubic-bezier(0.22, 0.72, 0.14, 1)",
};

function observeVisibleBlocks(): void {
  if (!visibilityObserver || !blocksRootRef.value) return;

  for (const element of blocksRootRef.value.querySelectorAll<HTMLElement>(
    ".block-wrap",
  )) {
    element.dataset.offscreen = "0";
    visibilityObserver.observe(element);
  }
}

watch(
  () => [activePage.value?.id, activePageGroupBlocks.value.length],
  async () => {
    if (!visibilityObserver) return;
    visibilityObserver.disconnect();
    await nextTick();
    observeVisibleBlocks();
  },
);

onMounted(async () => {
  visibilityObserver = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.target instanceof HTMLElement) {
          entry.target.dataset.offscreen = entry.isIntersecting ? "0" : "1";
        }
      }
    },
    {
      root: null,
      rootMargin: "140px 0px",
      threshold: 0.02,
    },
  );

  await nextTick();
  observeVisibleBlocks();
});

onBeforeUnmount(() => {
  visibilityObserver?.disconnect();
  visibilityObserver = null;
});
</script>
