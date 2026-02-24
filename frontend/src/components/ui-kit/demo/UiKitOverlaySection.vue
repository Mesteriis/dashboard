<template>
  <section class="ui-kit-section">
    <h2>Overlay & Actions</h2>

    <div class="ui-kit-grid cols-2">
      <article id="ui-node-modal" class="ui-kit-node ui-kit-stack">
        <h3>Modal</h3>
        <UiButton label="Open Modal" @click="modalOpen = true" />
        <p class="ui-kit-note">Modal независим и управляется только prop `open` + event `close`.</p>
      </article>

      <article id="ui-node-speeddial" class="ui-kit-node ui-kit-speed-zone">
        <h3>SpeedDial</h3>
        <p class="ui-kit-note">SpeedDial with 4 directions</p>
        <p class="ui-kit-note" v-if="speedActionLog">{{ speedActionLog }}</p>
        <div class="ui-kit-speed-grid">
          <UiSpeedDial :items="speedItems" direction="up" @action="onSpeedAction" />
          <UiSpeedDial :items="speedItems" direction="right" @action="onSpeedAction" />
          <UiSpeedDial :items="speedItems" direction="left" @action="onSpeedAction" />
          <UiSpeedDial :items="speedItems" direction="down" @action="onSpeedAction" />
        </div>
      </article>

      <article id="ui-node-dropdown-menu" class="ui-kit-node ui-kit-stack">
        <h3>Dropdown Menu</h3>
        <UiDropdownMenu
          label="Системное меню"
          :items="menuItems"
          @action="onMenuAction"
        />
        <p class="ui-kit-note" v-if="menuActionLog">{{ menuActionLog }}</p>
      </article>
    </div>

    <UiModal :open="modalOpen" title="Demo Modal" @close="modalOpen = false">
      <p>Контент модалки передаётся как slot, поведение закрытия — через event.</p>
      <template #footer>
        <UiButton variant="ghost" @click="modalOpen = false">Cancel</UiButton>
        <UiButton @click="modalOpen = false">Apply</UiButton>
      </template>
    </UiModal>
  </section>
</template>

<script setup lang="ts">
import { ref } from "vue";
import UiButton from "@/components/ui-kit/primitives/UiButton.vue";
import UiDropdownMenu from "@/components/ui-kit/primitives/UiDropdownMenu.vue";
import UiModal from "@/components/ui-kit/primitives/UiModal.vue";
import UiSpeedDial from "@/components/ui-kit/primitives/UiSpeedDial.vue";

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
