<template>
  <li
    class="tree-group-item"
    :class="{
      dragging:
        dragState.type === 'group' &&
        dragState.groupId === group.id &&
        isDirectGroupNodeLocal(group),
    }"
    :draggable="editMode && isDirectGroupNodeLocal(group)"
    @dragstart.stop="onGroupDragStart($event, group)"
    @dragend.stop="clearDragState"
    @dragover.stop="onGroupDragOver($event, group)"
    @drop.stop="onGroupDrop($event, group)"
  >
    <div class="tree-node-row">
      <button
        class="tree-node tree-group"
        :class="{ active: isGroupSelected(group.key) }"
        type="button"
        @click="toggleGroupNode(group.key)"
      >
        <span class="tree-caret" :class="{ open: isGroupExpanded(group.key) }"
          >▾</span
        >
        <component :is="resolveGroupIcon(group)" class="ui-icon tree-icon" />
        <span class="tree-text">{{ group.title }}</span>
        <span class="tree-meta">{{ groupTotalItems(group) }}</span>
      </button>

      <div
        v-if="editMode && isDirectGroupNodeLocal(group)"
        class="tree-inline-actions"
      >
        <GripVertical class="ui-icon tree-grip" />
        <button
          class="tree-mini-btn"
          type="button"
          title="Редактировать группу"
          @click.stop="editGroup(group.id)"
        >
          <Pencil class="ui-icon" />
        </button>
        <button
          class="tree-mini-btn"
          type="button"
          title="Добавить подгруппу"
          @click.stop="openCreateChooser(group.id)"
        >
          <Plus class="ui-icon" />
        </button>
        <button
          class="tree-mini-btn danger"
          type="button"
          title="Удалить группу"
          @click.stop="removeGroup(group.id)"
        >
          <Trash2 class="ui-icon" />
        </button>
      </div>
    </div>

    <ul v-show="isGroupExpanded(group.key)" class="tree-subgroups">
      <SidebarTreeSubgroupNode
        v-for="subgroup in group.subgroups"
        :key="subgroup.id"
        :group="group"
        :subgroup="subgroup"
      />
    </ul>
  </li>
</template>

<script setup lang="ts">
import { GripVertical, Pencil, Plus, Trash2 } from "lucide-vue-next";
import { useDashboardStore } from "@/stores/dashboardStore";
import SidebarTreeSubgroupNode from "@/components/ui-kit/composites/dashboard/UiSidebarTreeSubgroupNode.vue";
import { isDirectGroupNode as isDirectGroupNodeLocal } from "@/stores/dashboard/configTreeUtils";

defineProps({
  group: { type: Object, required: true },
});

const dashboard = useDashboardStore();

const {
  dragState,
  editMode,
  onGroupDragStart,
  clearDragState,
  onGroupDragOver,
  onGroupDrop,
  isGroupSelected,
  toggleGroupNode,
  isGroupExpanded,
  resolveGroupIcon,
  groupTotalItems,
  editGroup,
  openCreateChooser,
  removeGroup,
} = dashboard;
</script>
