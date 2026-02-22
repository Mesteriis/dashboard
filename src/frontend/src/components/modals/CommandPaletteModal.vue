<template>
  <BaseModal
    :open="commandPaletteOpen"
    backdrop-class="command-palette-backdrop"
    modal-class="command-palette-modal"
    @backdrop="closeCommandPalette"
  >
    <header class="command-palette-header">
      <div>
        <h3>Быстрый поиск</h3>
        <p>Сервисы и команды: имя, IP, tag, site</p>
      </div>
      <span class="command-palette-shortcut">{{ shortcutLabel }}</span>
    </header>

    <div class="command-palette-search">
      <Search class="ui-icon command-palette-search-icon" />
      <input
        ref="inputRef"
        class="command-palette-input"
        type="text"
        autocomplete="off"
        spellcheck="false"
        placeholder="Поиск сервиса или команды"
        :value="commandPaletteQuery"
        @input="setCommandPaletteQuery($event.target.value)"
        @keydown="handleInputKeydown"
      />
    </div>

    <ul
      v-if="commandPaletteResults.length"
      class="command-palette-list"
      role="listbox"
      aria-label="Быстрый поиск сервиса или команды"
    >
      <li
        v-for="(entry, index) in commandPaletteResults"
        :key="entry.id"
        v-motion="commandPaletteRowMotion(index)"
        class="command-palette-row"
      >
        <button
          class="command-palette-entry"
          :class="{
            active: index === commandPaletteActiveIndex,
            'is-action': entry.type === 'action',
          }"
          type="button"
          @mouseenter="setCommandPaletteActiveIndex(index)"
          @focus="setCommandPaletteActiveIndex(index)"
          @click="activateCommandPaletteEntry(entry)"
        >
          <span class="command-palette-entry-title">{{ entry.title }}</span>
          <span
            v-if="entry.type === 'action'"
            class="command-palette-entry-meta"
          >
            <span>Команда</span>
            <span>{{ entry.subgroupTitle }}</span>
          </span>
          <span v-else class="command-palette-entry-meta">
            <span>{{ entry.groupTitle }} / {{ entry.subgroupTitle }}</span>
            <span v-if="entry.host">{{ entry.host }}</span>
            <span v-if="entry.ip">{{ entry.ip }}</span>
            <span v-if="entry.site">site: {{ entry.site }}</span>
          </span>
        </button>

        <button
          v-if="entry.type === 'item'"
          class="ghost command-palette-copy"
          type="button"
          title="Скопировать URL"
          @click.stop="copyCommandPaletteEntryUrl(entry)"
        >
          <Copy class="ui-icon" />
        </button>
      </li>
    </ul>

    <p v-else class="command-palette-empty">Совпадений нет</p>
  </BaseModal>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { Copy, Search } from "lucide-vue-next";
import BaseModal from "../primitives/BaseModal.vue";
import { useDashboardStore } from "../../stores/dashboardStore.js";

const dashboard = useDashboardStore();
const {
  commandPaletteActiveIndex,
  commandPaletteOpen,
  commandPaletteQuery,
  commandPaletteResults,
  activateCommandPaletteEntry,
  activateCommandPaletteSelection,
  closeCommandPalette,
  copyCommandPaletteEntryUrl,
  moveCommandPaletteSelection,
  setCommandPaletteActiveIndex,
  setCommandPaletteQuery,
} = dashboard;

const inputRef = ref(null);
const shortcutLabel = /Mac|iPhone|iPad/i.test(
  globalThis.navigator?.platform || "",
)
  ? "⌘K"
  : "Ctrl+K";
const fxMode = ref(document.documentElement.dataset.fxMode || "full");

function syncFxMode() {
  fxMode.value = document.documentElement.dataset.fxMode || "full";
}

function focusSearchInput() {
  const applyFocus = () => {
    if (!inputRef.value) return;
    inputRef.value.focus();
    inputRef.value.select();
  };

  void nextTick(() => {
    applyFocus();
    window.requestAnimationFrame(() => {
      applyFocus();
    });
  });
}

function handleInputKeydown(event) {
  if (event.key === "ArrowDown") {
    event.preventDefault();
    moveCommandPaletteSelection(1);
    return;
  }

  if (event.key === "ArrowUp") {
    event.preventDefault();
    moveCommandPaletteSelection(-1);
    return;
  }

  if (event.key === "Enter") {
    event.preventDefault();
    activateCommandPaletteSelection();
    return;
  }

  if (event.key === "Escape") {
    event.preventDefault();
    closeCommandPalette();
  }
}

function commandPaletteRowMotion(index) {
  if (fxMode.value === "off") {
    return {
      initial: { opacity: 1, y: 0, scale: 1 },
      enter: { opacity: 1, y: 0, scale: 1, transition: { duration: 0 } },
    };
  }

  return {
    initial: { opacity: 0, y: 8, scale: 0.985 },
    enter: {
      opacity: 1,
      y: 0,
      scale: 1,
      transition: {
        duration: 220,
        delay: Math.min(index, 10) * 24,
      },
    },
  };
}

onMounted(() => {
  window.addEventListener("oko:fx-mode-change", syncFxMode);
  if (commandPaletteOpen.value) {
    focusSearchInput();
  }
});

onBeforeUnmount(() => {
  window.removeEventListener("oko:fx-mode-change", syncFxMode);
});

watch(
  () => commandPaletteOpen.value,
  (isOpen) => {
    if (!isOpen) return;
    focusSearchInput();
  },
  { flush: "post" },
);
</script>
