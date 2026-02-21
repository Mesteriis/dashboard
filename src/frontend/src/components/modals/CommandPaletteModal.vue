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
        <p>Имя, IP, tag, site</p>
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
        placeholder="Поиск сервиса"
        :value="commandPaletteQuery"
        @input="setCommandPaletteQuery($event.target.value)"
        @keydown="handleInputKeydown"
      />
    </div>

    <ul v-if="commandPaletteResults.length" class="command-palette-list" role="listbox" aria-label="Быстрый поиск сервиса">
      <li v-for="(entry, index) in commandPaletteResults" :key="entry.id" class="command-palette-row">
        <button
          class="command-palette-entry"
          :class="{ active: index === commandPaletteActiveIndex }"
          type="button"
          @mouseenter="setCommandPaletteActiveIndex(index)"
          @focus="setCommandPaletteActiveIndex(index)"
          @click="activateCommandPaletteEntry(entry)"
        >
          <span class="command-palette-entry-title">{{ entry.title }}</span>
          <span class="command-palette-entry-meta">
            <span>{{ entry.groupTitle }} / {{ entry.subgroupTitle }}</span>
            <span v-if="entry.host">{{ entry.host }}</span>
            <span v-if="entry.ip">{{ entry.ip }}</span>
            <span v-if="entry.site">site: {{ entry.site }}</span>
          </span>
        </button>

        <button class="ghost command-palette-copy" type="button" title="Скопировать URL" @click.stop="copyCommandPaletteEntryUrl(entry)">
          <Copy class="ui-icon" />
        </button>
      </li>
    </ul>

    <p v-else class="command-palette-empty">Совпадений нет</p>
  </BaseModal>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Copy, Search } from 'lucide-vue-next'
import BaseModal from '../primitives/BaseModal.vue'
import { useDashboardStore } from '../../stores/dashboardStore.js'

const dashboard = useDashboardStore()
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
  toggleCommandPalette,
} = dashboard

const inputRef = ref(null)
const shortcutLabel = /Mac|iPhone|iPad/i.test(globalThis.navigator?.platform || '') ? '⌘K' : 'Ctrl+K'

function handleInputKeydown(event) {
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    moveCommandPaletteSelection(1)
    return
  }

  if (event.key === 'ArrowUp') {
    event.preventDefault()
    moveCommandPaletteSelection(-1)
    return
  }

  if (event.key === 'Enter') {
    event.preventDefault()
    activateCommandPaletteSelection()
    return
  }

  if (event.key === 'Escape') {
    event.preventDefault()
    closeCommandPalette()
  }
}

function handleWindowKeydown(event) {
  const isShortcut = (event.metaKey || event.ctrlKey) && !event.altKey && !event.shiftKey && event.key.toLowerCase() === 'k'
  if (!isShortcut && event.key !== 'Escape') return

  if (isShortcut) {
    event.preventDefault()
    toggleCommandPalette()
    return
  }

  if (commandPaletteOpen.value && event.key === 'Escape') {
    event.preventDefault()
    closeCommandPalette()
  }
}

watch(
  () => commandPaletteOpen.value,
  async (isOpen) => {
    if (!isOpen) return
    await nextTick()
    inputRef.value?.focus()
    inputRef.value?.select()
  }
)

onMounted(() => {
  window.addEventListener('keydown', handleWindowKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleWindowKeydown)
})
</script>
