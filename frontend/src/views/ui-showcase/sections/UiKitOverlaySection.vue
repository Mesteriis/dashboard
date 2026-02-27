<template>
  <section class="ui-kit-section">
    <div class="ui-kit-grid cols-2">
      <UiShowcaseNode
        v-show="isNodeVisible('ui-node-modal')"
        id="ui-node-modal"
        class="ui-kit-stack"
        group-label="Overlay & Actions"
        element-label="UiModal"
        :value="modalOpen"
        :api="SHOWCASE_NODE_API['ui-node-modal']"
      >
        <UiButton label="Open Modal" @click="modalOpen = true" />
      </UiShowcaseNode>

      <UiShowcaseNode
        v-show="isNodeVisible('ui-node-speeddial')"
        id="ui-node-speeddial"
        class="ui-kit-speed-zone"
        group-label="Overlay & Actions"
        element-label="UiSpeedDial"
        :value="speedActionLog"
        :api="SHOWCASE_NODE_API['ui-node-speeddial']"
      >
        <div class="ui-kit-speed-grid">
          <UiSpeedDial
            :items="speedItems"
            direction="up"
            @action="onSpeedAction"
          />
          <UiSpeedDial
            :items="speedItems"
            direction="right"
            @action="onSpeedAction"
          />
          <UiSpeedDial
            :items="speedItems"
            direction="left"
            @action="onSpeedAction"
          />
          <UiSpeedDial
            :items="speedItems"
            direction="down"
            @action="onSpeedAction"
          />
        </div>
      </UiShowcaseNode>

      <UiShowcaseNode
        v-show="isNodeVisible('ui-node-dropdown-menu')"
        id="ui-node-dropdown-menu"
        class="ui-kit-stack"
        group-label="Overlay & Actions"
        element-label="UiDropdownMenu"
        :value="menuActionLog"
        :api="SHOWCASE_NODE_API['ui-node-dropdown-menu']"
      >
        <UiDropdownMenu
          label="Системное меню"
          :items="menuItems"
          @action="onMenuAction"
        />
      </UiShowcaseNode>
    </div>

    <UiModal :open="modalOpen" title="Demo Modal" @close="modalOpen = false">
      <p>
        Контент модалки передаётся как slot, поведение закрытия — через event.
      </p>
      <template #footer>
        <UiButton variant="ghost" @click="modalOpen = false">Cancel</UiButton>
        <UiButton @click="modalOpen = false">Apply</UiButton>
      </template>
    </UiModal>
  </section>
</template>

<script setup lang="ts">
import { ref } from "vue";
import UiButton from "@/ui/actions/UiButton.vue";
import UiDropdownMenu from "@/primitives/overlays/UiDropdownMenu.vue";
import UiModal from "@/primitives/overlays/UiModal.vue";
import UiShowcaseNode from "@/views/ui-showcase/components/UiShowcaseNode.vue";
import { SHOWCASE_NODE_API } from "@/views/ui-showcase/showcaseNodeApi";
import UiSpeedDial from "@/primitives/overlays/UiSpeedDial.vue";

const props = withDefaults(
  defineProps<{
    activeNodeId?: string;
  }>(),
  {
    activeNodeId: "",
  },
);

function isNodeVisible(nodeId: string): boolean {
  if (!props.activeNodeId) return true;
  return props.activeNodeId === nodeId;
}

const modalOpen = ref(false);
const speedActionLog = ref("");
const menuActionLog = ref("");

const speedItems = [
  { id: "edit", label: "Edit", icon: "✎" },
  { id: "clone", label: "Clone", icon: "⧉" },
  { id: "delete", label: "Delete", icon: "⌫" },
];

const menuItems = [
  { id: "kiosk", label: "Режим киоска" },
  { id: "profile", label: "Профиль" },
  { id: "pleiad_lock", label: "Блокировка -> Плияды" },
  { id: "exit", label: "Выход", danger: true },
];

function onSpeedAction(id: string): void {
  speedActionLog.value = `Last speed action: ${id}`;
}

function onMenuAction(id: string): void {
  menuActionLog.value = `Last menu action: ${id}`;
}
</script>
