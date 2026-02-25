<template>
  <li
    class="tree-item-row"
    :class="{
      dragging: dragState.type === 'item' && dragState.itemId === item.id,
    }"
    :draggable="editMode"
    @dragstart.stop="onItemDragStart($event, group.id, subgroup.id, item.id)"
    @dragend.stop="clearDragState"
    @dragover.stop="onItemDragOver($event, group.id, subgroup.id, item.id)"
    @drop.stop="onItemDrop($event, group.id, subgroup.id, item.id)"
  >
    <div class="tree-node-row">
      <UiSidebarListItem
        variant="item"
        :active="isItemSelected(item.id)"
        @click="selectItemNode(group.key, subgroup.id, item.id)"
      >
        <span class="health-dot" :class="healthClass(item.id)"></span>
        <img
          v-if="itemFaviconSrc(item)"
          :src="itemFaviconSrc(item)"
          class="service-favicon tree-item-favicon"
          alt=""
          loading="lazy"
          referrerpolicy="no-referrer"
          @error="markItemFaviconFailed(item)"
        />
        <component
          v-else
          :is="resolveItemIcon(item)"
          class="ui-icon tree-icon tree-item-icon"
        />
        <span class="tree-text">{{ item.title }}</span>
      </UiSidebarListItem>

      <div v-if="editMode" class="tree-inline-actions">
        <GripVertical class="ui-icon tree-grip" />
        <button
          class="tree-mini-btn"
          type="button"
          title="Редактировать элемент"
          @click.stop="editItem(group.id, subgroup.id, item.id)"
        >
          <Pencil class="ui-icon" />
        </button>
        <button
          class="tree-mini-btn danger"
          type="button"
          title="Удалить элемент"
          @click.stop="removeItem(group.id, subgroup.id, item.id)"
        >
          <Trash2 class="ui-icon" />
        </button>
      </div>
    </div>
  </li>
</template>

<script setup lang="ts">
import { GripVertical, Pencil, Trash2 } from "lucide-vue-next";
import { useDashboardStore } from "@/features/stores/dashboardStore";
import UiSidebarListItem from "@/components/navigation/UiSidebarListItem.vue";

defineProps({
  group: { type: Object, required: true },
  subgroup: { type: Object, required: true },
  item: { type: Object, required: true },
});

const dashboard = useDashboardStore();

const {
  dragState,
  editMode,
  onItemDragStart,
  clearDragState,
  onItemDragOver,
  onItemDrop,
  isItemSelected,
  selectItemNode,
  healthClass,
  itemFaviconSrc,
  markItemFaviconFailed,
  resolveItemIcon,
  editItem,
  removeItem,
} = dashboard;
</script>
