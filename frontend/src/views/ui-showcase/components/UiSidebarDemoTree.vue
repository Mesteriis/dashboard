<template>
  <section class="sidebar-tree ui-kit-sidebar-tree-demo">
    <ul class="tree-root">
      <li class="tree-group-item">
        <div class="tree-node-row">
          <UiSidebarListItem
            variant="group"
            :active="activeNode === 'group'"
            @click="setActiveNode('group')"
          >
            <span class="tree-caret open">▾</span>
            <LayoutGrid class="ui-icon tree-icon" />
            <span class="tree-text">Core Services</span>
            <span class="tree-meta">3</span>
          </UiSidebarListItem>
        </div>

        <ul class="tree-subgroups">
          <li class="tree-subgroup-item">
            <div class="tree-node-row">
              <UiSidebarListItem
                variant="subgroup"
                :active="activeNode === 'subgroup'"
                @click="setActiveNode('subgroup')"
              >
                <Boxes class="ui-icon tree-icon tree-sub-icon" />
                <span class="tree-text">Main</span>
                <span class="tree-meta">3</span>
              </UiSidebarListItem>
            </div>

            <ul class="tree-items">
              <li class="tree-item-row">
                <div class="tree-node-row">
                  <UiSidebarListItem
                    variant="item"
                    :active="activeNode === 'new-service'"
                    @click="setActiveNode('new-service')"
                  >
                    <span class="health-dot unknown"></span>
                    <Boxes class="ui-icon tree-icon tree-item-icon" />
                    <span class="tree-text">Новый сервис</span>
                  </UiSidebarListItem>
                </div>
              </li>

              <li class="tree-item-row">
                <div class="tree-node-row">
                  <UiSidebarListItem
                    variant="item"
                    :active="activeNode === 'proxmox'"
                    @click="setActiveNode('proxmox')"
                  >
                    <span class="health-dot ok"></span>
                    <span class="ui-kit-proxmox-mark" aria-hidden="true"
                      >✕</span
                    >
                    <span class="tree-text">proxmox</span>
                  </UiSidebarListItem>
                </div>
              </li>

              <li class="tree-item-row">
                <div class="tree-node-row">
                  <UiSidebarListItem
                    variant="item"
                    :active="activeNode === 'test2'"
                    @click="setActiveNode('test2')"
                  >
                    <span class="health-dot down"></span>
                    <Boxes class="ui-icon tree-icon tree-item-icon" />
                    <span class="tree-text">test2</span>
                  </UiSidebarListItem>
                </div>
              </li>
            </ul>
          </li>
        </ul>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { Boxes, LayoutGrid } from "lucide-vue-next";
import UiSidebarListItem from "@/components/navigation/UiSidebarListItem.vue";

type NodeTreeNodeId =
  | "group"
  | "subgroup"
  | "new-service"
  | "proxmox"
  | "test2";

const props = withDefaults(
  defineProps<{
    modelValue?: NodeTreeNodeId;
  }>(),
  {
    modelValue: "proxmox",
  },
);

const emit = defineEmits<{
  "update:modelValue": [NodeTreeNodeId];
}>();

const activeNode = computed<NodeTreeNodeId>(
  () => props.modelValue || "proxmox",
);

function setActiveNode(nodeId: NodeTreeNodeId): void {
  emit("update:modelValue", nodeId);
}
</script>

<style scoped>
.ui-kit-sidebar-tree-demo {
  min-height: 0;
  overflow: hidden;
  padding: 10px;
}

.ui-kit-proxmox-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #ff9100;
  font-size: 1.2rem;
  line-height: 1;
  width: 14px;
  height: 14px;
}
</style>
