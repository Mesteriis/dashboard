<template>
  <li
    class="tree-subgroup-item"
    :class="{ dragging: dragState.type === 'subgroup' && dragState.subgroupId === subgroup.id }"
    :draggable="editMode"
    @dragstart.stop="onSubgroupDragStart($event, group.id, subgroup.id)"
    @dragend.stop="clearDragState"
    @dragover.stop="onSubgroupDragOver($event, group.id, subgroup.id)"
    @drop.stop="onSubgroupDrop($event, group.id, subgroup.id)"
  >
    <div class="tree-node-row">
      <button class="tree-node tree-subgroup" :class="{ active: isSubgroupSelected(group.key, subgroup.id) }" type="button" @click="selectSubgroupNode(group.key, subgroup.id)">
        <component :is="resolveSubgroupIcon(subgroup)" class="ui-icon tree-icon tree-sub-icon" />
        <span class="tree-text">{{ subgroup.title }}</span>
        <span class="tree-meta">{{ subgroupTotalItems(subgroup) }}</span>
      </button>
      <div v-if="editMode" class="tree-inline-actions">
        <GripVertical class="ui-icon tree-grip" />
        <button class="tree-mini-btn" type="button" title="Редактировать подгруппу" @click.stop="editSubgroup(group.id, subgroup.id)">
          <Pencil class="ui-icon" />
        </button>
        <button class="tree-mini-btn" type="button" title="Добавить элемент" @click.stop="addItem(group.id, subgroup.id)">
          <Plus class="ui-icon" />
        </button>
        <button class="tree-mini-btn danger" type="button" title="Удалить подгруппу" @click.stop="removeSubgroup(group.id, subgroup.id)">
          <Trash2 class="ui-icon" />
        </button>
      </div>
    </div>

  </li>
</template>

<script setup>
import { GripVertical, Pencil, Plus, Trash2 } from 'lucide-vue-next'
import { useDashboardStore } from '../../stores/dashboardStore.js'

defineProps({
  group: { type: Object, required: true },
  subgroup: { type: Object, required: true },
})

const dashboard = useDashboardStore()

const {
  dragState,
  editMode,
  onSubgroupDragStart,
  clearDragState,
  onSubgroupDragOver,
  onSubgroupDrop,
  isSubgroupSelected,
  selectSubgroupNode,
  resolveSubgroupIcon,
  subgroupTotalItems,
  editSubgroup,
  addItem,
  removeSubgroup,
} = dashboard
</script>
