<template>
  <section class="sidebar-tree" aria-label="UI kit navigation tree">
    <ul v-if="groups.length" class="tree-root">
      <li
        v-for="group in groups"
        :key="group.id"
        class="tree-group-item"
      >
        <div class="tree-node-row">
          <UiSidebarListItem
            variant="group"
            :active="activeGroup === group.id"
            @click="emit('group-change', group.id)"
          >
            <span class="tree-caret open">▾</span>
            <LayoutGrid class="ui-icon tree-icon" />
            <span class="tree-text">{{ group.label }}</span>
            <span class="tree-meta">{{ group.items.length }}</span>
          </UiSidebarListItem>
        </div>

        <ul class="tree-subgroups">
          <li
            v-for="section in group.sections"
            :key="section.id"
            class="tree-subgroup-item"
          >
            <div class="tree-node-row">
              <UiSidebarListItem
                variant="subgroup"
                :active="isSectionActive(group.id, section.id)"
                @click="onSectionClick(group.id, section.id)"
              >
                <Boxes class="ui-icon tree-icon tree-sub-icon" />
                <span class="tree-text">{{ section.label }}</span>
                <span class="tree-meta">{{ section.items.length }}</span>
              </UiSidebarListItem>
            </div>

            <ul v-if="section.items.length" class="tree-items">
              <li
                v-for="item in section.items"
                :key="item.id"
                class="tree-item-row"
              >
                <div class="tree-node-row">
                  <UiSidebarListItem
                    variant="item"
                    :active="activeNodeId === item.id"
                    @click="emit('node-click', item.id, group.id)"
                  >
                    <Boxes class="ui-icon tree-icon tree-item-icon" />
                    <span class="tree-text">{{ item.label }}</span>
                  </UiSidebarListItem>
                </div>
              </li>
            </ul>
          </li>
        </ul>
      </li>
    </ul>

    <p v-else class="tree-empty">No matches for search query.</p>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { Boxes, LayoutGrid } from "lucide-vue-next";
import type { UiKitPrimitiveGroup } from "@/views/ui-showcase/sections/showcaseRegistry";
import UiSidebarListItem from "@/components/navigation/UiSidebarListItem.vue";

type GroupFilterId = UiKitPrimitiveGroup["id"];

const props = defineProps<{
  groups: UiKitPrimitiveGroup[];
  activeGroup: GroupFilterId;
  activeNodeId: string;
}>();

const emit = defineEmits<{
  "group-change": [GroupFilterId];
  "node-click": [string, GroupFilterId];
}>();

const sectionItemsMap = computed(() => {
  const map = new Map<string, string[]>();
  for (const group of props.groups) {
    for (const section of group.sections) {
      map.set(
        `${group.id}:${section.id}`,
        section.items.map((item) => item.id),
      );
    }
  }
  return map;
});

function isSectionActive(groupId: GroupFilterId, sectionId: string): boolean {
  const key = `${groupId}:${sectionId}`;
  const itemIds = sectionItemsMap.value.get(key);
  if (!itemIds?.length) return false;
  return itemIds.includes(props.activeNodeId);
}

function onSectionClick(groupId: GroupFilterId, sectionId: string): void {
  const key = `${groupId}:${sectionId}`;
  const firstNodeId = sectionItemsMap.value.get(key)?.[0] || "";
  if (firstNodeId) {
    emit("node-click", firstNodeId, groupId);
    return;
  }
  emit("group-change", groupId);
}
</script>
