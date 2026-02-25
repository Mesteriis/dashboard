<template>
  <section class="ui-kit-page panel">
    <div class="ui-kit-page__content ui-kit-page__content--tabbed">
      <p v-if="!hasVisibleItems" class="ui-kit-note">
        No primitives match the current filter.
      </p>
      <p v-else-if="!resolvedNodeId" class="ui-kit-note">
        Select an element in the sidebar to open its tab.
      </p>

      <UiKitFormSection
        v-else-if="resolvedNodeId && activeGroup === 'forms'"
        :active-node-id="resolvedNodeId"
      />
      <UiKitDataSection
        v-else-if="resolvedNodeId && activeGroup === 'data'"
        :active-node-id="resolvedNodeId"
      />
      <UiKitLayoutSection
        v-else-if="resolvedNodeId && activeGroup === 'layout'"
        :active-node-id="resolvedNodeId"
      />
      <UiKitOverlaySection
        v-else-if="resolvedNodeId && activeGroup === 'overlay'"
        :active-node-id="resolvedNodeId"
      />
      <UiKitHtmlSection
        v-else-if="resolvedNodeId"
        :active-node-id="resolvedNodeId"
      />
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, watch } from "vue";
import { UI_KIT_SHOWCASE_GROUPS } from "@/views/ui-showcase/sections/showcaseRegistry";
import UiKitDataSection from "@/views/ui-showcase/sections/UiKitDataSection.vue";
import UiKitFormSection from "@/views/ui-showcase/sections/UiKitFormSection.vue";
import UiKitHtmlSection from "@/views/ui-showcase/sections/UiKitHtmlSection.vue";
import UiKitLayoutSection from "@/views/ui-showcase/sections/UiKitLayoutSection.vue";
import UiKitOverlaySection from "@/views/ui-showcase/sections/UiKitOverlaySection.vue";

const emit = defineEmits<{
  close: [];
  "update:activeNodeId": [string];
}>();

const props = withDefaults(
  defineProps<{
    activeGroup?: string;
    activeNodeId?: string;
    hasVisibleItems?: boolean;
  }>(),
  {
    activeGroup: "forms",
    activeNodeId: "",
    hasVisibleItems: true,
  },
);

function findFirstNodeIdByGroup(groupId: string): string {
  const group = UI_KIT_SHOWCASE_GROUPS.find((entry) => entry.id === groupId);
  return group?.items[0]?.id ?? "";
}

const resolvedNodeId = computed(() => {
  if (!props.hasVisibleItems) return "";
  if (!props.activeNodeId) return "";
  const group = UI_KIT_SHOWCASE_GROUPS.find(
    (entry) => entry.id === props.activeGroup,
  );
  const availableIds = group?.items.map((item) => item.id) || [];
  if (!availableIds.length) return "";
  if (props.activeNodeId && availableIds.includes(props.activeNodeId)) {
    return props.activeNodeId;
  }
  return findFirstNodeIdByGroup(props.activeGroup);
});

watch(
  () => resolvedNodeId.value,
  (nextId) => {
    if (!nextId) return;
    if (nextId === props.activeNodeId) return;
    emit("update:activeNodeId", nextId);
  },
  { immediate: true },
);
</script>

<style scoped>
.ui-kit-page__content--tabbed :deep(.ui-kit-grid.cols-2) {
  grid-template-columns: minmax(0, 1fr);
}

.ui-kit-page__content--tabbed :deep(.ui-kit-section) {
  align-content: start;
}
</style>
